# bin/export_savedsearches_btool_v2.py
import re
import subprocess
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Optional
from jinja2 import Environment, FileSystemLoader

# Try to import logger, fallback to print if not available
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from logger import get_logger
    logger = get_logger("export")
    USE_LOGGER = True
except ImportError:
    USE_LOGGER = False
    # Fallback logger that uses print
    class FallbackLogger:
        def info(self, msg): print(msg)
        def debug(self, msg): pass  # Ignore debug in fallback
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def setLevel(self, level): pass  # Dummy method for compatibility
    logger = FallbackLogger()

# ==== Determine base directory ====
ROOT_DIR = Path(__file__).resolve().parent.parent

# ==== Load configuration from config.txt ====
def load_config(path: Path = ROOT_DIR / "config.txt") -> Dict[str, str]:
    """Load configuration with environment variable support"""
    config = {}
    
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    
    # Override with environment variables
    env_prefix = "CONF2MD_"
    for key in list(config.keys()):
        env_key = f"{env_prefix}{key}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    
    return config

config = load_config()

# ==== Set up file logging if LOG_FILE env var is set ====
LOG_FILE = os.environ.get("LOG_FILE")
LOG_FILE_PATH = Path(LOG_FILE).resolve() if LOG_FILE else None
if LOG_FILE_PATH:
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USE_LOGGER:
        # Reconfigure logger with file handler
        from logger import setup_logger
        logger = setup_logger("export", log_file=LOG_FILE_PATH)

# ==== Configurable paths and filenames ====
EXPORT_BASE = (ROOT_DIR / config.get("EXPORT_BASE", "export/savedsearches")).resolve()
TEMPLATE_DIR = (ROOT_DIR / config.get("TEMPLATE_DIR", "templates")).resolve()
TEMPLATE_NAME = config.get("TEMPLATE_NAME", "example.md.j2")
SPLUNK_BIN = config.get("SPLUNK_BIN", "/opt/splunk/bin/")
splunk_exe = Path(SPLUNK_BIN) / "splunk"

# ==== Optional filter from config ====
FILTER_KEY = config.get("NOTABLE_FILTER_KEY")
FILTER_VALUE = config.get("NOTABLE_FILTER_VALUE")

# ==== Helper functions ====

def extract_context_keys(template_dir: Path, template_name: str) -> List[str]:
    """Extract all `context["key"]` references from the Jinja2 template."""
    path = template_dir / template_name
    if not path.exists():
        logger.error(f"Template not found: {path}")
        raise FileNotFoundError(f"Template not found: {path}")
    
    text = path.read_text(encoding="utf-8")
    keys = sorted(set(re.findall(r'context\["(.*?)"\]', text)))
    logger.debug(f"Extracted template keys: {keys}")
    return keys

def sanitize_filename(name: str) -> str:
    """Sanitize file name to be safe for the file system."""
    sanitized = re.sub(r"[^\w\-_.]", "_", name)
    return sanitized[:180]

def get_btool_savedsearches() -> Dict[str, Dict[str, str]]:
    """Run `splunk btool` and parse the savedsearches output into a dictionary."""
    if not splunk_exe.is_file():
        logger.error(f"Splunk binary not found at: {splunk_exe}")
        raise FileNotFoundError(f"Splunk binary not found at: {splunk_exe}")
    
    cmd = [str(splunk_exe), "btool", "savedsearches", "list", "--debug"]
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=300  # 5 minute timeout
        )
    except subprocess.TimeoutExpired:
        logger.error("btool command timed out after 5 minutes")
        raise
    
    if result.returncode != 0:
        logger.error(f"btool failed with exit code {result.returncode}: {result.stderr}")
        raise RuntimeError(f"Error while executing btool: {result.stderr}")

    savedsearches = defaultdict(dict)
    current_name = None

    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue

        right = parts[1].strip()
        if right.startswith("[") and right.endswith("]"):
            current_name = right[1:-1].strip()
        elif current_name and "=" in right:
            key, val = map(str.strip, right.split("=", 1))
            savedsearches[current_name][key] = val

    logger.info(f"Found {len(savedsearches)} saved searches")
    return dict(savedsearches)

def export_savedsearches(dry_run: bool = False) -> Dict[str, str]:
    """
    Exports matching savedsearches as Markdown using a Jinja2 template.
    
    Args:
        dry_run: If True, only show what would be exported without writing files
        
    Returns:
        Dictionary mapping filenames to export status
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    
    try:
        template = env.get_template(TEMPLATE_NAME)
    except Exception as e:
        logger.error(f"Failed to load template {TEMPLATE_NAME}: {e}")
        raise

    template_keys = extract_context_keys(TEMPLATE_DIR, TEMPLATE_NAME)
    
    if not dry_run:
        EXPORT_BASE.mkdir(parents=True, exist_ok=True)
    
    searches = get_btool_savedsearches()
    results = {}
    exported_count = 0
    filtered_count = 0
    skipped_count = 0

    for title, content in searches.items():
        if FILTER_KEY and FILTER_VALUE:
            if content.get(FILTER_KEY) != FILTER_VALUE:
                filtered_count += 1
                logger.debug(f"Filtered out: {title}")
                continue

        context = {k: content.get(k, "(not available)") for k in template_keys}
        context["title"] = title

        filename = sanitize_filename(title) + ".md"
        filepath = EXPORT_BASE / filename

        if dry_run:
            logger.info(f"[DRY RUN] Would export: {filename}")
            results[filename] = "Would be exported"
            skipped_count += 1
        else:
            try:
                with filepath.open("w", encoding="utf-8") as f:
                    f.write(template.render(context=context, title=title))
                
                log_msg = f"btool export: {filename}: ✓ Exported"
                logger.info(log_msg)
                
                # Also write to log file for backward compatibility
                if LOG_FILE_PATH and not USE_LOGGER:
                    with LOG_FILE_PATH.open("a", encoding="utf-8") as log:
                        log.write(log_msg + "\n")
                
                results[filename] = "✓ Exported"
                exported_count += 1
            except Exception as e:
                logger.error(f"Failed to export {filename}: {e}")
                results[filename] = f"✗ Error: {e}"
    
    # Summary message
    if dry_run:
        logger.info(f"[DRY RUN] Complete: Would export {skipped_count} searches, filtered {filtered_count}")
    else:
        logger.info(f"Export complete: {exported_count} exported, {filtered_count} filtered")
    
    return results

# ==== Entry point ====
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export Splunk saved searches to Markdown")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be exported without writing files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Adjust logging level if verbose
    if args.verbose and USE_LOGGER:
        import logging
        logger.setLevel(logging.DEBUG)
    
    try:
        logger.info("Starting Splunk saved searches export...")
        if args.dry_run:
            logger.info("Running in DRY RUN mode - no files will be written")
        
        results = export_savedsearches(dry_run=args.dry_run)
        
        # Print summary of results
        if results:
            logger.info("\nExport Summary:")
            success_count = sum(1 for status in results.values() if "✓" in status or "Would be exported" in status)
            error_count = sum(1 for status in results.values() if "✗" in status)
            
            logger.info(f"Total searches processed: {len(results)}")
            if args.dry_run:
                logger.info(f"Would export: {success_count} files")
            else:
                logger.info(f"Successfully exported: {success_count} files")
            
            if error_count > 0:
                logger.error(f"Failed exports: {error_count} files")
                
            # Show first 10 results as examples
            if args.verbose or args.dry_run:
                logger.info("\nDetailed results (first 10):")
                for i, (filename, status) in enumerate(sorted(results.items())):
                    if i >= 10:
                        logger.info(f"... and {len(results) - 10} more")
                        break
                    logger.info(f"  {filename}: {status}")
        else:
            logger.warning("No searches found to export!")
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)