# bin/upload_to_wikijs_v2.py
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Tuple, List, Optional
import requests
import re
import os
import sys
import time
from functools import wraps

# Try to import logger, fallback to print if not available
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from logger import get_logger
    logger = get_logger("upload")
    USE_LOGGER = True
except ImportError:
    USE_LOGGER = False
    class FallbackLogger:
        def info(self, msg): print(msg)
        def debug(self, msg): pass
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def setLevel(self, level): pass  # Dummy method for compatibility
    logger = FallbackLogger()

# ==== Determine base directory ====
ROOT_DIR = Path(__file__).resolve().parent.parent

# ==== Load configuration ====
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
    
    # Check for API token in common env vars
    for env_name in ["WIKIJS_API_TOKEN", "WIKIJS_TOKEN", "API_TOKEN"]:
        if env_name in os.environ:
            config["WIKIJS_API_TOKEN"] = os.environ[env_name]
            break
    
    return config

config = load_config()

# ==== Set up file logging if LOG_FILE env var is set ====
LOG_FILE = os.environ.get("LOG_FILE")
LOG_FILE_PATH = Path(LOG_FILE).resolve() if LOG_FILE else None
if LOG_FILE_PATH and USE_LOGGER:
    from logger import setup_logger
    logger = setup_logger("upload", log_file=LOG_FILE_PATH)

# ==== Configurable parameters ====
WIKIJS_URL = config.get("WIKIJS_URL", "https://wikijs.local:3000/graphql")
API_TOKEN = config.get("WIKIJS_API_TOKEN", "")
MARKDOWN_DIR = (ROOT_DIR / config.get("WIKIJS_MARKDOWN_DIR", "export/savedsearches")).resolve()
BASE_WIKI_PATH = config.get("WIKIJS_BASE_PATH", "/a/b/c")
LOCALE = config.get("WIKIJS_LOCALE", "en")
MAX_PARALLEL_UPLOADS = int(config.get("WIKIJS_MAX_PARALLEL_UPLOADS", "5"))
MAX_RETRIES = int(config.get("WIKIJS_MAX_RETRIES", "3"))
RETRY_DELAY = float(config.get("WIKIJS_RETRY_DELAY", "2.0"))

# ==== Retry decorator ====
def retry(max_attempts: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator to retry failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            
            # This should never happen if max_attempts > 0, but let's be safe
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"All {max_attempts} attempts failed")
        return wrapper
    return decorator

# ==== Utility functions ====

def sanitize_title(filename: Path) -> str:
    """Converts a filename into a readable title by replacing underscores and whitespace."""
    return re.sub(r"[_\s]+", " ", filename.stem)

@retry()
def _graphql_request(query: str, variables: Optional[Dict] = None) -> Dict:
    """Sends a GraphQL request to Wiki.js and returns the response as JSON."""
    if not API_TOKEN:
        raise ValueError("API_TOKEN not configured. Please set WIKIJS_API_TOKEN in config.txt or environment.")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query, "variables": variables or {}}
    
    logger.debug(f"GraphQL Request to {WIKIJS_URL}")
    
    response = None
    try:
        response = requests.post(
            WIKIJS_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except ValueError as e:
        # response könnte None sein, wenn der Fehler vor der Zuweisung auftritt
        response_text = response.text if response else "No response"
        logger.error(f"Invalid JSON response: {response_text}")
        raise Exception(f"Error parsing response: {e}")

def get_all_pages() -> Dict[str, int]:
    """Fetches a list of all existing pages from Wiki.js as a dict: {path: id}."""
    query = """
    query {
      pages {
        list(orderBy: TITLE) {
          id
          path
        }
      }
    }
    """
    
    logger.info("Fetching existing Wiki.js pages...")
    result = _graphql_request(query)
    
    pages = result["data"]["pages"]["list"]
    pages_dict = {page["path"]: page["id"] for page in pages}
    
    logger.info(f"Found {len(pages_dict)} existing pages")
    return pages_dict

def create_page(title: str, content: str, path: str) -> None:
    """Creates a new Wiki.js page via GraphQL mutation."""
    logger.info(f"Creating new page: {title}")
    
    mutation = """
    mutation CreatePage($content: String!, $description: String!, $editor: String!, $isPublished: Boolean!, $isPrivate: Boolean!, $locale: String!, $path: String!, $tags: [String]!, $title: String!) {
      pages {
        create(
          content: $content,
          description: $description,
          editor: $editor,
          isPublished: $isPublished,
          isPrivate: $isPrivate,
          locale: $locale,
          path: $path,
          tags: $tags,
          title: $title
        ) {
          responseResult {
            succeeded
            message
          }
          page {
            id
          }
        }
      }
    }
    """
    
    variables = {
        "content": content,
        "description": f"Automatically generated from Saved Search: {title}",
        "editor": "markdown",
        "isPublished": True,
        "isPrivate": False,
        "locale": LOCALE,
        "path": path,
        "tags": [],
        "title": title
    }
    
    result = _graphql_request(mutation, variables)
    status = result["data"]["pages"]["create"]["responseResult"]
    
    if not status["succeeded"]:
        raise Exception(f"Error creating page '{title}': {status['message']}")
    
    logger.info(f"Successfully created page: {title}")

def update_page(page_id: int, title: str, content: str, path: str) -> None:
    """Updates an existing Wiki.js page by ID."""
    logger.info(f"Updating existing page: {title} (ID: {page_id})")
    
    mutation = """
    mutation UpdatePage($id: Int!, $title: String!, $content: String!, $editor: String!, $description: String!, $locale: String!, $path: String!, $tags: [String!]) {
      pages {
        update(id: $id, title: $title, content: $content, editor: $editor, description: $description, locale: $locale, path: $path, tags: $tags) {
          responseResult {
            succeeded
            message
          }
        }
      }
    }
    """
    
    variables = {
        "id": page_id,
        "title": title,
        "content": content,
        "editor": "markdown",
        "description": f"Automatically updated from Saved Search: {title}",
        "locale": LOCALE,
        "path": path,
        "tags": []
    }
    
    result = _graphql_request(mutation, variables)
    status = result["data"]["pages"]["update"]["responseResult"]
    
    if not status["succeeded"]:
        raise Exception(f"Error updating page '{title}': {status['message']}")
    
    logger.info(f"Successfully updated page: {title}")

def process_file(file: Path, pages_by_path: Dict[str, int]) -> Tuple[str, str]:
    """Processes a single markdown file: creates or updates the corresponding Wiki.js page."""
    title = sanitize_title(file)
    content = file.read_text(encoding="utf-8")
    wiki_path = f"{BASE_WIKI_PATH}/{file.stem}".lstrip("/")
    page_id = pages_by_path.get(wiki_path)

    try:
        if page_id:
            update_page(page_id, title, content, wiki_path)
        else:
            create_page(title, content, wiki_path)
        result = "✓ Success"
    except Exception as e:
        result = f"✗ Error: {e}"
        logger.error(f"Failed to process {file.name}: {e}")

    # Log for backward compatibility
    log_msg = f"wikijs upload: {file.name}: {result}"
    if LOG_FILE_PATH and not USE_LOGGER:
        with LOG_FILE_PATH.open("a", encoding="utf-8") as log:
            log.write(log_msg + "\n")

    return (file.name, result)

# ==== Main execution logic ====
def upload_all_markdown_files(dry_run: bool = False) -> Dict[str, str]:
    """
    Upload all markdown files to Wiki.js
    
    Args:
        dry_run: If True, only show what would be uploaded
        
    Returns:
        Dictionary mapping filenames to upload status
    """
    if not MARKDOWN_DIR.exists():
        logger.error(f"Markdown directory not found: {MARKDOWN_DIR}")
        raise FileNotFoundError(f"Markdown directory not found: {MARKDOWN_DIR}")
    
    files = list(MARKDOWN_DIR.glob("*.md"))
    if not files:
        logger.warning(f"No markdown files found in {MARKDOWN_DIR}")
        return {}
    
    logger.info(f"Found {len(files)} markdown files to process")
    
    if dry_run:
        logger.info("[DRY RUN] Would upload the following files:")
        results = {}
        for file in files:
            logger.info(f"  - {file.name}")
            results[file.name] = "Would be uploaded"
        return results
    
    try:
        pages_by_path = get_all_pages()
    except Exception as e:
        logger.error(f"Failed to fetch existing pages: {e}")
        raise
    
    results = {}
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_UPLOADS) as executor:
        futures = {executor.submit(process_file, file, pages_by_path): file for file in files}
        
        for future in as_completed(futures):
            try:
                filename, result = future.result()
                results[filename] = result
                
                if "Success" in result:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                file = futures[future]
                logger.error(f"Unexpected error processing {file.name}: {e}")
                results[file.name] = f"✗ Unexpected error: {e}"
                error_count += 1
    
    logger.info(f"Upload complete: {success_count} successful, {error_count} failed")
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload Markdown files to Wiki.js")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without actually uploading")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    if args.verbose and USE_LOGGER:
        import logging
        logger.setLevel(logging.DEBUG)
    
    try:
        results = upload_all_markdown_files(dry_run=args.dry_run)
        
        # Print summary
        if results:
            print("\nResults:")
            for filename, status in sorted(results.items()):
                print(f"  {filename}: {status}")
                
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)