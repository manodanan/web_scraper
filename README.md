# Backend & API Finder CLI (`backend-finder`)

A machine-learning-powered command-line utility for web application auditing, API discovery, and web-scraping analysis.

`backend-finder` automatically intercepts live browser network traffic, scans JavaScript bundles and embedded framework states, and uses a calibrated machine learning pipeline to identify true backend microservices while filtering out third-party telemetry, ads, and static asset noise.

---

## Key Features

- **Machine Learning Classification**: Uses Scikit-Learn (Calibrated Gradient Boosting Classifier, character-level TF-IDF n-grams, Shannon entropy, and domain-affinity features) to rank endpoints by backend probability. The model trains on a built-in labelled corpus each time the tool starts — there is no separate training step and no model file to download.
- **Live Browser Interception**: Employs Playwright with anti-detection configuration (Chromium automation flags plus a `navigator.webdriver` patch) to capture background `XHR`, `Fetch`, and `GraphQL` network traffic. Image, stylesheet, font, and media requests are discarded at capture time.
- **Multi-Engine Support**: Runs against Chromium, Firefox, or WebKit via `--browser`. Missing browser binaries are installed automatically on first run.
- **Static Asset Extraction**: Downloads the page's first 10 JavaScript bundles and regex-scans them for API routes, and extracts embedded `__NEXT_DATA__` and other JSON-typed `<script>` state tags.
- **Terminal Integration**: Provides a full command-line interface (`argparse`), ANSI color formatting, column-aligned output tables, and a `man` page.
- **Structured JSON Exports**: Saves metadata, HTTP request methods, headers, and confidence scores to `backend_report.json`.

---

## How It Works

The scan runs in two phases against the target URL:

1. **Static analysis** — fetches the page with `requests`, extracts embedded JSON state tags, then downloads and regex-scans linked JavaScript bundles for API-looking routes.
2. **Live interception** — drives a real browser to the page, hooks every outgoing request, scrolls to trigger lazy-loaded calls, and scores each request with the ML classifier.

Requests scoring **at or above** `--threshold` are reported as backend APIs; everything below is filed as third-party noise. Both groups are written to the JSON report.

---

## Installation

### Prerequisites
- Python 3.9+
- Linux or macOS

### Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the backend-finder package
pip install -e .

# 3. (Optional) Pre-install the Playwright browser binary
playwright install chromium
```

Step 3 is optional: if the requested browser binary is missing, `backend-finder` installs it automatically on first run. Pre-installing it just moves that one-off download out of your first scan. Use `playwright install firefox` or `playwright install webkit` if you plan to run those engines.

---

## Usage

The package installs two equivalent entry points, `backend-finder` and `backend_finder`. You can also run the script directly with `python backend_finder.py`:

### Basic Usage

```bash
backend-finder https://example.com/
```

### Advanced Options

```bash
# Run with a custom ML confidence threshold (70%) and output file path
backend-finder https://dummyjson.com/ -t 0.70 -o custom_report.json

# Choose the browser engine used for interception
backend-finder https://example.com/ --browser firefox
backend-finder https://example.com/ --browser webkit

# Run browser in visible mode (non-headless)
backend-finder https://example.com/ --no-headless

# Enable verbose network tracing output
backend-finder https://example.com/ -v

# Disable ANSI colors for scripts or log files
backend-finder https://example.com/ --no-color
```

### Help and Manual Page

```bash
# Display CLI help menu
backend-finder --help

# View the built-in manual page
backend-finder --man
# OR
man ./backend_finder.1
```

---

## Command Line Reference

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `target` | Positional | Target web application URL | `https://dummyjson.com/` |
| `--url` | `-u` | Target web application URL (overrides the positional argument) | Positional URL |
| `--output` | `-o` | Output JSON report file path | `backend_report.json` |
| `--threshold` | `-t` | ML confidence score cutoff (0.0 to 1.0); requests scoring at or above it are reported as backend APIs | `0.50` |
| `--browser` | | Browser engine for interception: `chromium`, `firefox`, or `webkit` | `chromium` |
| `--no-headless` | | Launch browser in visible GUI mode | Headless |
| `--verbose` | `-v` | Enable verbose network request logging | Off |
| `--no-color` | | Disable ANSI terminal color codes | Enabled for TTY |
| `--man` | | Display the manual page (`man`, falling back to `cat`) | Off |

A URL without a scheme is accepted — `https://` is prepended automatically. Colors are also disabled automatically when output is piped to a file or another command.

---

## Report Format

The JSON report written to `--output` contains:

| Key | Contents |
| :--- | :--- |
| `target_url` / `browser_engine` | Scan parameters used |
| `summary` | Counts of total captured requests, backend APIs, filtered noise, and JS-discovered endpoints |
| `backend_apis` | Requests scoring at or above the threshold, with method, type, URL, headers, and score |
| `all_requests` | Every captured request, including those below the threshold |
| `js_discovered_endpoints` | API routes found in JavaScript bundles, ranked by score |
| `embedded_state` | Previews of embedded JSON state tags found in the page HTML |

---

## Project Structure

```text
web_scraper/
├── backend_finder.py         # Main CLI application executable & network interceptor
├── ml_backend_classifier.py  # Machine Learning classification engine & feature pipeline
├── backend_finder.1          # roff/groff man page documentation
├── pyproject.toml            # Python package configuration
├── setup.py                  # Installation & entry point script
├── backend_report.json       # Generated scan report (default output path)
└── README.md                 # Project documentation
```

---

## License

MIT License. Developed for web scraping, backend auditing, and API security discovery workflows.
