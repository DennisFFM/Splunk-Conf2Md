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
- ✅ Comprehensive logging with colored console output
- ✅ Retry mechanism for failed uploads
- ✅ Dry-run mode for testing
- ✅ Environment variable support for sensitive data
- ✅ Type hints for better code maintainability

---

## 📋 Requirements

- Python 3.7+
- Splunk instance with btool access
- Wiki.js instance with GraphQL API enabled
- API token for Wiki.js

---

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/splunk-conf2md.git
cd splunk-conf2md
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the sample configuration:
```bash
cp config.txt.sample config.txt
```

4. Edit `config.txt` and add your settings (see Configuration section)

---

## ⚙️ Configuration

### Configuration File (`config.txt`)

All relevant parameters are maintained in `config.txt`:

```ini
### Splunk Export ###
EXPORT_BASE = export/savedsearches
TEMPLATE_DIR = templates
TEMPLATE_NAME = example.md.j2
SPLUNK_BIN = /opt/splunk/bin/

# Optional filter - uncomment to enable
#NOTABLE_FILTER_KEY = action.notable
#NOTABLE_FILTER_VALUE = 1

### WikiJS Import ###
WIKIJS_URL = http://wikijs.local:3000/graphql
WIKIJS_API_TOKEN = <your-api-token>
WIKIJS_MARKDOWN_DIR = export/savedsearches
WIKIJS_BASE_PATH = /a/b/c
WIKIJS_LOCALE = en
WIKIJS_MAX_PARALLEL_UPLOADS = 5
WIKIJS_MAX_RETRIES = 3
WIKIJS_RETRY_DELAY = 2.0
```

### Environment Variables

For security, you can override any configuration value using environment variables:

```bash
# Use CONF2MD_ prefix for any config value
export CONF2MD_WIKIJS_API_TOKEN="your-secret-token"

# Or use common environment variable names
export WIKIJS_API_TOKEN="your-secret-token"
export WIKIJS_TOKEN="your-secret-token"
export API_TOKEN="your-secret-token"
```

---

## 📖 Usage

### Basic Usage

Run both export and upload:
```bash
python bin/main.py
```

### Advanced Options

```bash
# Only export saved searches (no upload)
python bin/main.py --export-only

# Only upload existing markdown files (no export)
python bin/main.py --upload-only

# Dry run - show what would be done without doing it
python bin/main.py --dry-run

# Enable verbose logging
python bin/main.py -v

# Combine options
python bin/main.py --export-only --dry-run -v
```

### Direct Script Usage

You can also run the scripts individually:

```bash
# Export only
python bin/export_savedsearches_btool.py --dry-run -v

# Upload only
python bin/upload_to_wikijs.py --dry-run -v
```

---

## 📝 Templates

Templates use Jinja2 syntax. Create custom templates in the `templates/` directory.

Example template (`templates/example.md.j2`):
```jinja2
## Search Name
{{ context["title"] | default('(No Title)') }}

## Description
{{ context["description"] | default('(No Description)') }}

## Search Query
{{ context["search"] | default('(No Search Query)') }}

## Schedule
{{ context["cron_schedule"] | default('Not scheduled') }}

## Actions
{% if context["action.notable"] == "1" %}
- ⚠️ Creates Notable Event
{% endif %}
{% if context["action.email"] == "1" %}
- 📧 Sends Email Alert
{% endif %}
```

---

## 🔍 Troubleshooting

### Common Issues

1. **"Splunk binary not found"**
   - Verify `SPLUNK_BIN` path in config.txt
   - Ensure the user has execute permissions

2. **"API token not configured"**
   - Set `WIKIJS_API_TOKEN` in config.txt or environment
   - Verify the token has appropriate permissions in Wiki.js

3. **"GraphQL errors"**
   - Check Wiki.js logs for detailed error messages
   - Verify the API endpoint URL is correct
   - Ensure Wiki.js GraphQL API is enabled

### Logging

Logs are stored in the `logs/` directory with timestamps:
```
logs/wikijs_upload_20240115_143022.log
```

To increase log verbosity, use the `-v` flag or check the log file for detailed information.

---

## 📊 Example Output

### Console Output (Normal)
```
==============================================================
Splunk-Conf2Md started at 2024-01-15 14:30:22
Log file: logs/wikijs_upload_20240115_143022.log
==============================================================
Starting export phase...
Executing export_savedsearches_btool.py...
Found 245 saved searches
Exported: Security_Notable_Authentication_Failed.md
Exported: Security_Notable_Malware_Detected.md
Export complete: 42 exported, 203 filtered
Successfully executed export_savedsearches_btool.py
Export phase completed successfully
Starting upload phase...
Executing upload_to_wikijs.py...
Fetching existing Wiki.js pages...
Found 38 existing pages
Updating existing page: Security Notable Authentication Failed
Creating new page: Security Notable Malware Detected
Upload complete: 42 successful, 0 failed
Successfully executed upload_to_wikijs.py
Upload phase completed successfully
==============================================================
All operations completed successfully!
Log file: logs/wikijs_upload_20240115_143022.log
==============================================================
```

### Dry Run Output
```
[DRY RUN] Would export: Security_Notable_Authentication_Failed.md
[DRY RUN] Would export: Security_Notable_Malware_Detected.md
...
[DRY RUN] Would upload the following files:
  - Security_Notable_Authentication_Failed.md
  - Security_Notable_Malware_Detected.md
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- [Splunk](https://www.splunk.com/) for the powerful search platform
- [Wiki.js](https://js.wiki/) for the modern documentation platform
- [Jinja2](https://jinja.palletsprojects.com/) for the templating engine