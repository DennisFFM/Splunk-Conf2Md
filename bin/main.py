# bin/main.py
from pathlib import Path
from datetime import datetime
import os
import subprocess
import sys
import argparse
from typing import Optional, Dict

# Set up root and script paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT_DIR / "bin"
EXPORT_SCRIPT = BIN_DIR / "export_savedsearches_btool.py"
UPLOAD_SCRIPT = BIN_DIR / "upload_to_wikijs.py"

def load_config(path: Path = ROOT_DIR / "config.txt") -> Dict[str, str]:
    """Load configuration"""
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

def run_script(script_path: Path, log_file: Path, extra_args: Optional[list] = None) -> None:
    """
    Run a Python script with proper error handling
    
    Args:
        script_path: Path to the script
        log_file: Path to the log file
        extra_args: Additional arguments to pass to the script
    """
    print(f"\n→ Executing {script_path.name}...\n")
    
    cmd = ["python", str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            text=True,
            env={**os.environ, "LOG_FILE": str(log_file)},
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Error while executing {script_path.name} (Exit Code: {result.returncode})"
            )
            
        print(f"✓ Successfully executed {script_path.name}")
        
    except Exception as e:
        print(f"✗ Failed to execute {script_path.name}: {e}")
        raise

def main(export_only: bool = False, 
         upload_only: bool = False, 
         dry_run: bool = False,
         verbose: bool = False) -> None:
    """
    Main execution function
    
    Args:
        export_only: Only run export, skip upload
        upload_only: Only run upload, skip export
        dry_run: Show what would be done without actually doing it
        verbose: Enable verbose logging
    """
    # Set up logging
    execution_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    config = load_config()
    
    log_file_pattern = config.get("WIKIJS_LOG_FILE", "logs/wikijs_upload_{execution_time}.log")
    log_file_path = ROOT_DIR / log_file_pattern.format(execution_time=execution_time)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print(f"Splunk-Conf2Md started at {datetime.now()}")
    print(f"Log file: {log_file_path}")
    print("="*60)
    
    # Validate scripts exist
    for script in [EXPORT_SCRIPT, UPLOAD_SCRIPT]:
        if not script.exists():
            print(f"✗ Script not found: {script}")
            sys.exit(1)
    
    # Build extra arguments
    extra_args = []
    if dry_run:
        extra_args.append("--dry-run")
    if verbose:
        extra_args.append("--verbose")
    
    try:
        # Run export if not upload-only
        if not upload_only:
            print("Starting export phase...")
            run_script(EXPORT_SCRIPT, log_file_path, extra_args)
            print("Export phase completed successfully")
        else:
            print("Skipping export phase (--upload-only)")
        
        # Run upload if not export-only
        if not export_only:
            print("Starting upload phase...")
            run_script(UPLOAD_SCRIPT, log_file_path, extra_args)
            print("Upload phase completed successfully")
        else:
            print("Skipping upload phase (--export-only)")
        
        print("="*60)
        print("All operations completed successfully!")
        print(f"Log file: {log_file_path}")
        print("="*60)
        
    except Exception as e:
        print(f"✗ Operation failed: {e}")
        print("="*60)
        print(f"FAILED! Check log file: {log_file_path}")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Splunk-Conf2Md: Export Splunk saved searches to Wiki.js",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Run both export and upload
  %(prog)s --export-only       # Only export saved searches
  %(prog)s --upload-only       # Only upload existing markdown files
  %(prog)s --dry-run          # Show what would be done without doing it
  %(prog)s -v                 # Enable verbose logging
        """
    )
    
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only run export, skip upload"
    )
    parser.add_argument(
        "--upload-only", 
        action="store_true",
        help="Only run upload, skip export"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.export_only and args.upload_only:
        parser.error("--export-only and --upload-only are mutually exclusive")
    
    main(
        export_only=args.export_only,
        upload_only=args.upload_only,
        dry_run=args.dry_run,
        verbose=args.verbose
    )