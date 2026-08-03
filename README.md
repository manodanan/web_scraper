# Backend & API Finder CLI (`backend-finder`)

A machine-learning-powered command-line utility for web application auditing, API discovery, and web-scraping analysis.

`backend-finder` automatically intercepts live browser network traffic, scans JavaScript bundles and embedded framework states, and uses a calibrated machine learning pipeline to identify true backend microservices while filtering out third-party telemetry, ads, and static asset noise.

---

## Key Features

- **Machine Learning Classification**: Uses Scikit-Learn (Calibrated Gradient Boosting Classifier, character-level TF-IDF n-grams, Shannon entropy, and domain-affinity transformers) to rank endpoints by backend probability.
- **Live Browser Interception**: Employs Playwright with stealth anti-detection configurations to capture background `XHR`, `Fetch`, `WebSocket`, and `GraphQL` network traffic.
- **Static Asset Extraction**: Downloads JavaScript bundles and extracts embedded React, Next.js (`__NEXT_DATA__`), and Nuxt JSON states.
- **Terminal Integration**: Provides a full command-line interface (`argparse`), ANSI color formatting, column-aligned output tables, and a Linux manual page (`man`).
- **Structured JSON Exports**: Saves metadata, HTTP request methods, headers, and confidence scores to `backend_report.json`.

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

# 3. Install Playwright Chromium browser binary
playwright install chromium
```

---

## Usage

You can execute the command directly using `backend-finder` or `python backend_finder.py`:

### Basic Usage

```bash
backend-finder https://trendyol.com/
```

### Advanced Options

```bash
# Run with a custom ML confidence threshold (70%) and output file path
backend-finder https://dummyjson.com/ -t 0.70 -o custom_report.json

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

# View the built-in Linux manual page
backend-finder --man
# OR
man ./backend_finder.1
```

---

## Command Line Reference

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `target` | Positional | Target web application URL | `https://dummyjson.com/` |
| `--url` | `-u` | Target web application URL | Positional URL |
| `--output` | `-o` | Output JSON report file path | `backend_report.json` |
| `--threshold` | `-t` | ML confidence score threshold (0.0 to 1.0) | `0.50` |
| `--no-headless` | | Launch browser in visible GUI mode | Headless |
| `--verbose` | `-v` | Enable verbose network request logging | Off |
| `--no-color` | | Disable ANSI terminal color codes | Enabled for TTY |
| `--man` | | Display the Linux manual page | Off |

---

## Project Structure

```text
web_scraper/
├── backend_finder.py         # Main CLI application executable & network interceptor
├── ml_backend_classifier.py  # Machine Learning classification engine & feature pipeline
├── backend_finder.1          # Linux roff/groff man page documentation
├── pyproject.toml            # Python package configuration
├── setup.py                  # Installation & entry point script
└── README.md                 # Project documentation
```

---

## License

MIT License. Developed for web scraping, backend auditing, and API security discovery workflows.
