# Splunk-Conf2Md

**Splunk-Conf2Md** is a tool for automatically exporting Splunk SavedSearches to Markdown files and subsequently publishing them to [Wiki.js](https://wiki.js.org/) via the GraphQL API.

---

## 🔍 Features

- ✅ Export of Splunk `savedsearches.conf` via `btool`
- ✅ Jinja2 template support for flexible Markdown formatting
- ✅ Optional filter (e.g., only Notable searches)
- ✅ Automatic upload as pages to Wiki.js
- ✅ Support for updates to existing pages (no duplicates)
- ✅ Configurable parallelization for uploads
- ✅ Central log file per execution
- ✅ Full control via `main.py`

---

## ⚙️ Configuration (`config.txt`)

All relevant parameters are maintained in `config.txt`:

```ini
# Paths
EXPORT_BASE = export/savedsearches
TEMPLATE_DIR = templates
TEMPLATE_NAME = example.md.j2
SPLUNK_BIN = /opt/splunk/bin/

# Filter (optional)
NOTABLE_FILTER_KEY = action.notable
NOTABLE_FILTER_VALUE = 1

# Wiki.js Settings
WIKIJS_URL = http://wikijs.local:3000/graphql
WIKIJS_API_TOKEN = <your-api-token>
WIKIJS_MARKDOWN_DIR = export/savedsearches
WIKIJS_BASE_PATH = /a/b/c
WIKIJS_LOCALE = en
WIKIJS_MAX_PARALLEL_UPLOADS = 5
WIKIJS_LOG_FILE = logs/wikijs_upload_{execution_time}.log
