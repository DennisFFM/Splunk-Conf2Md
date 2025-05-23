import re
import subprocess
import os
from pathlib import Path
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
import json

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

# ==== Configurable paths and filenames ====
EXPORT_BASE = (ROOT_DIR / config.get("EXPORT_BASE", "export/savedsearches")).resolve()
TEMPLATE_DIR = (ROOT_DIR / config.get("TEMPLATE_DIR", "templates")).resolve()
TEMPLATE_NAME = config.get("TEMPLATE_NAME", "example.md.j2")
SPLUNK_BIN = config.get("SPLUNK_BIN", "/opt/splunk/bin/")
splunk_exe = Path(SPLUNK_BIN) / "splunk"
if not splunk_exe.is_file():
    raise FileNotFoundError(f"Splunk binary not found at: {splunk_exe}")

# ==== Optional filter from config ====
FILTER_KEY = config.get("NOTABLE_FILTER_KEY")
FILTER_VALUE = config.get("NOTABLE_FILTER_VALUE")

# ==== Optional log file via environment ====
LOG_FILE = os.environ.get("LOG_FILE")
LOG_FILE_PATH = Path(LOG_FILE).resolve() if LOG_FILE else None
if LOG_FILE_PATH:
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ==== Helper functions ====

def extract_context_keys(template_dir, template_name):
    """Extract all `context["key"]` references from the Jinja2 template."""
    path = template_dir / template_name
    text = path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'context\["(.*?)"\]', text)))

def sanitize_filename(name):
    """Sanitize file name to be safe for the file system."""
    name = re.sub(r"[^\w\-_.]", "_", name)
    return name[:180]

def get_btool_savedsearches():
    """Run `splunk btool` and parse the savedsearches output into a dictionary."""
    cmd = [str(splunk_exe), "btool", "savedsearches", "list", "--debug"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
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

    return savedsearches

def format_risk_table(risk_data_raw):
    """Convert JSON list of risk parameters to a markdown table (if valid). Ignores 'threat_object_*' entries."""
    try:
        risk_data = json.loads(risk_data_raw)
    except Exception:
        return None
    if not isinstance(risk_data, list) or not risk_data:
        return None

    # Filter only valid risk entries (i.e. those with all 3 expected keys)
    valid_entries = [
        entry for entry in risk_data
        if all(k in entry for k in ("risk_object_field", "risk_object_type", "risk_score"))
    ]

    if not valid_entries:
        return None

    rows = ["| Risk Object Field | Risk Object Type | Risk Score |",
            "|-------------------|------------------|------------|"]
    for entry in valid_entries:
        rows.append(f"| {entry['risk_object_field']} | {entry['risk_object_type']} | {entry['risk_score']} |")
    return "\n".join(rows)


def export_savedsearches():
    """Exports matching savedsearches as Markdown using a Jinja2 template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_NAME)

    template_keys = extract_context_keys(TEMPLATE_DIR, TEMPLATE_NAME)

    EXPORT_BASE.mkdir(parents=True, exist_ok=True)
    searches = get_btool_savedsearches()

    for title, content in searches.items():
        if FILTER_KEY and FILTER_VALUE:
            if content.get(FILTER_KEY) != FILTER_VALUE:
                continue

        context = {k: content.get(k, "(not available)") for k in template_keys}
        context["title"] = title

        # Add parsed risk table if available
        raw_risk_value = content.get("action.risk.param._risk")
        if raw_risk_value:
            risk_table_md = format_risk_table(raw_risk_value)
            if risk_table_md:
                context["risk_table_markdown"] = risk_table_md
                
        filename = sanitize_filename(title) + ".md"
        filepath = EXPORT_BASE / filename

        with filepath.open("w", encoding="utf-8") as f:
            f.write(template.render(context=context, title=title))

        log_entry = f"btool export: {filepath.name}: ✓ Exported"
        print(log_entry)
        if LOG_FILE_PATH:
            with LOG_FILE_PATH.open("a", encoding="utf-8") as log:
                log.write(log_entry + "\n")

# ==== Entry point ====
if __name__ == "__main__":
    export_savedsearches()
