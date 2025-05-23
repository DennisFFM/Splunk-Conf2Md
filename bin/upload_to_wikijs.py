from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
import re
import os

# ==== Determine base directory ====
ROOT_DIR = Path(__file__).resolve().parent.parent

# ==== Load configuration from config.txt ====
def load_config(path=ROOT_DIR / "config.txt"):
    config = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    return config

config = load_config()

# ==== Configurable parameters ====
WIKIJS_URL = config.get("WIKIJS_URL", "https://wikijs.local:3000/graphql")
API_TOKEN = config.get("WIKIJS_API_TOKEN", "")
MARKDOWN_DIR = (ROOT_DIR / config.get("WIKIJS_MARKDOWN_DIR", "export/savedsearches")).resolve()
BASE_WIKI_PATH = config.get("WIKIJS_BASE_PATH", "/a/b/c")
LOCALE = config.get("WIKIJS_LOCALE", "en")
MAX_PARALLEL_UPLOADS = int(config.get("WIKIJS_MAX_PARALLEL_UPLOADS", "5"))

# ==== Optional log file via environment ====
LOG_FILE = os.environ.get("LOG_FILE")
LOG_FILE_PATH = Path(LOG_FILE).resolve() if LOG_FILE else None
if LOG_FILE_PATH:
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ==== Utility functions ====

def sanitize_title(filename: Path) -> str:
    """Converts a filename into a readable title by replacing underscores and whitespace."""
    return re.sub(r"[_\s]+", " ", filename.stem)

def _graphql_request(query, variables=None):
    """Sends a GraphQL request to Wiki.js and returns the response as JSON."""
    response = requests.post(
        WIKIJS_URL,
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"query": query, "variables": variables or {}}
    )
    try:
        return response.json()
    except Exception:
        raise Exception(f"Error parsing response: {response.text}")

def get_all_pages():
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
    result = _graphql_request(query)
    if "errors" in result:
        raise Exception(f"Error while fetching existing pages: {result}")
    pages = result["data"]["pages"]["list"]
    return {page["path"]: page["id"] for page in pages}

def create_page(title, content, path):
    """Creates a new Wiki.js page via GraphQL mutation."""
    print(f"→ Creating new page: {title}")
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

def update_page(page_id, title, content, path):
    """Updates an existing Wiki.js page by ID."""
    print(f"→ Updating existing page: {title}")
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

def process_file(file: Path, pages_by_path: dict) -> tuple[str, str]:
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

    log_entry = f"wikijs upload: {file.name}: {result}"
    print(log_entry)
    if LOG_FILE_PATH:
        with LOG_FILE_PATH.open("a", encoding="utf-8") as log:
            log.write(log_entry + "\n")

    return (file.name, result)

# ==== Main execution logic ====
def upload_all_markdown_files():
    print("→ Fetching existing Wiki.js pages ...")
    pages_by_path = get_all_pages()
    files = list(MARKDOWN_DIR.glob("*.md"))

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_UPLOADS) as executor:
        futures = [executor.submit(process_file, file, pages_by_path) for file in files]
        for future in as_completed(futures):
            filename, result = future.result()
            print(f"{filename}: {result}")

if __name__ == "__main__":
    upload_all_markdown_files()
