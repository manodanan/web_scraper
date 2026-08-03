# Backend & API Finder CLI (`backend-finder`)

A machine-learning-powered command-line utility for web application auditing, API discovery, and web-scraping analysis.

Most sites render their content from a private JSON API that never appears in the HTML. `backend-finder` drives a real browser at a page, watches every request it makes, and uses a calibrated ML pipeline to tell you which of those requests are the site's own backend — and which are ads, analytics, and asset noise.

> **Scan responsibly.** Only point this tool at sites you own or have permission to test. The tutorial below uses a public sandbox built for scraping practice.

---

## Tutorial

This walkthrough takes about five minutes and ends with you holding a real site's undocumented API endpoint. Every command and every block of output below is from an actual run — you should see the same thing.

### What you'll need

- Python 3.9 or newer (`python3 --version`)
- macOS or Linux
- ~150 MB of disk for the Chromium download (one time, automatic)

### Step 1 — Install

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

That installs the dependencies and puts a `backend-finder` command on your PATH. Confirm it worked:

```bash
backend-finder --help
```

If you get `ModuleNotFoundError: No module named 'backend_finder'`, jump to [Troubleshooting](#troubleshooting) — there's a one-line fix.

You don't need to install a browser separately. The first scan downloads Chromium automatically if it isn't already there.

### Step 2 — Run your first scan

We'll scan [quotes.toscrape.com/scroll](https://quotes.toscrape.com/scroll), a practice site that loads its quotes over AJAX instead of putting them in the HTML. Open it in a browser first — the quotes appear as you scroll, and they're nowhere in "view source." That's the API we're going to find.

```bash
backend-finder https://quotes.toscrape.com/scroll
```

The scan takes about fifteen seconds and prints:

```text
==================================================
 BACKEND & API FINDER CLI
==================================================
Target URL : https://quotes.toscrape.com/scroll
Engine     : Chromium
Threshold  : 50% ML Confidence
Output File: backend_report.json

[+] [1/2] Scanning static HTML & JavaScript assets...
    [INFO] Found 1 JavaScript bundle scripts.

[+] [2/2] Intercepting Live Network Traffic with Chromium...
    [INFO] Navigating Chromium to: https://quotes.toscrape.com/scroll
    [INFO] Initial Response: HTTP 200

==================================================
 BACKEND DISCOVERY RESULTS SUMMARY
==================================================
Backend APIs Identified            : 1
Third-Party & Noise Requests Filtered: 2

Top Identified Backend API Endpoints:
----------------------------------------------------------------------------------------
SCORE    | METHOD | TYPE     | URL
----------------------------------------------------------------------------------------
85.0%    | GET    | xhr      | https://quotes.toscrape.com/api/quotes?page=1

[+] Full report saved to: /path/to/backend_report.json
```

There it is: `https://quotes.toscrape.com/api/quotes?page=1`. Open that URL directly and you'll get clean JSON — no HTML parsing, no CSS selectors to maintain. Change `page=1` to `page=2` and you have pagination.

### Step 3 — Understand what you're looking at

The scan captured three requests and scored each from 0.0 to 1.0:

| Score | Type | URL | Why |
| :--- | :--- | :--- | :--- |
| `0.85` | `xhr` | `/api/quotes?page=1` | First-party host, XHR, `/api/` in the path — the backend |
| `0.10` | `script` | `/static/jquery.js` | Static asset paths are capped low on sight |
| `0.0994` | `document` | `/scroll` | The page itself, not an API call |

Anything scoring at or above the threshold (default `0.50`) is reported as a backend API. The other two were filtered as noise — which is what "Third-Party & Noise Requests Filtered: 2" means.

Note that image, stylesheet, font, and media requests are dropped before scoring, so they never show up at all. What you see is already filtered.

### Step 4 — Read the JSON report

The terminal table is a preview. The full detail — including headers and every filtered request — lands in `backend_report.json`:

```bash
jq '.summary' backend_report.json
```

```json
{
  "total_captured_requests": 3,
  "backend_apis_count": 1,
  "third_party_noise_count": 2,
  "js_endpoints_count": 0
}
```

Pull out just the endpoints that cleared the threshold:

```bash
jq -r '.backend_apis[] | "\(.score)  \(.method)  \(.url)"' backend_report.json
```

```text
0.85  GET  https://quotes.toscrape.com/api/quotes?page=1
```

Or inspect everything that was captured, including what got filtered:

```bash
jq -r '.all_requests[] | "\(.score)  \(.type)  \(.url)"' backend_report.json
```

```text
0.85  xhr  https://quotes.toscrape.com/api/quotes?page=1
0.1  script  https://quotes.toscrape.com/static/jquery.js
0.0994  document  https://quotes.toscrape.com/scroll
```

`backend_apis` entries also carry the full request `headers`, which is where you'll find the `Authorization` or `X-API-Key` values a site sends — useful when the endpoint doesn't work from `curl` on its own.

### Step 5 — Tune the threshold

`--threshold` is the confidence cutoff. Raise it and the tool gets stricter:

```bash
backend-finder https://quotes.toscrape.com/scroll -t 0.90
```

```text
Backend APIs Identified            : 0
Third-Party & Noise Requests Filtered: 3

Top Identified Backend API Endpoints:
----------------------------------------------------------------------------------------
SCORE    | METHOD | TYPE     | URL
----------------------------------------------------------------------------------------
85.0%    | GET    | xhr      | https://quotes.toscrape.com/api/quotes?page=1
10.0%    | GET    | script   | https://quotes.toscrape.com/static/jquery.js
9.9%     | GET    | document | https://quotes.toscrape.com/scroll
```

At `0.90` nothing qualifies, so the count drops to zero. When no endpoint clears the bar the table falls back to showing the highest-scoring captures anyway — that's deliberate, so you can see what you *nearly* caught and pick a better number. Lower the threshold when a site's API is on an unusual domain; raise it when you're drowning in false positives.

### Step 6 — The other options worth knowing

Watch the browser work, which is the fastest way to see why a scan came back empty:

```bash
backend-finder https://quotes.toscrape.com/scroll --no-headless -v
```

Scan with a different engine — some sites behave differently outside Chromium:

```bash
backend-finder https://quotes.toscrape.com/scroll --browser firefox
```

The Firefox and WebKit binaries download automatically the first time you use them.

Write somewhere other than the default, and drop the ANSI colors for logs:

```bash
backend-finder https://quotes.toscrape.com/scroll -o quotes-api.json --no-color
```

Colors switch off by themselves when output isn't a terminal, so piping to a file is already clean.

### Where to go next

Try it on a site you're actually interested in. Sites that render server-side (plain HTML, no JavaScript) will come back nearly empty — that's a real answer, and it means scraping the HTML is your only route. Sites built on React, Vue, or Next.js almost always surface something.

---

## Command Line Reference

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `target` | Positional | Target web application URL | `https://dummyjson.com/` |
| `--url` | `-u` | Target URL (overrides the positional argument) | Positional URL |
| `--output` | `-o` | Output JSON report file path | `backend_report.json` |
| `--threshold` | `-t` | Confidence cutoff (0.0–1.0); requests scoring at or above it are reported as backend APIs | `0.50` |
| `--browser` | | Engine for interception: `chromium`, `firefox`, or `webkit` | `chromium` |
| `--no-headless` | | Launch the browser in visible GUI mode | Headless |
| `--verbose` | `-v` | Print every intercepted request as it's captured | Off |
| `--no-color` | | Disable ANSI terminal color codes | Enabled for TTY |
| `--man` | | Display the manual page and exit | Off |

A URL without a scheme is fine — `https://` is prepended automatically, so `backend-finder example.com` works.

Full documentation is also available as a man page:

```bash
backend-finder --man
```

---

## Report Format

| Key | Contents |
| :--- | :--- |
| `target_url` / `browser_engine` | Scan parameters used |
| `summary` | Counts of total captured requests, backend APIs, filtered noise, and JS-discovered endpoints |
| `backend_apis` | Requests at or above the threshold, with method, type, URL, headers, and score |
| `all_requests` | Every captured request, including those below the threshold, sorted by score |
| `js_discovered_endpoints` | API routes found by regex-scanning JavaScript bundles, ranked by score |
| `embedded_state` | Truncated previews of embedded JSON state tags, such as `__NEXT_DATA__` |

---

## How Scoring Works

Each scan runs two phases:

1. **Static analysis** — fetches the page with `requests`, extracts embedded JSON state tags, then downloads the first 10 linked JavaScript bundles and regex-scans them for API-looking routes.
2. **Live interception** — drives a real browser to the page, hooks every outgoing request, scrolls to trigger lazy-loaded calls, and scores each request.

Scoring combines a Scikit-Learn pipeline (Calibrated Gradient Boosting over character-level TF-IDF n-grams, plus structural features: Shannon entropy, path depth, digit ratio, domain affinity, header and method signals) with a few hard rules:

- Static asset extensions (`.js`, `.css`, `.png`, …) are capped at `0.10`
- Known tracker domains (Google Analytics, GTM, Hotjar, Sentry, DoubleClick, …) are capped at `0.05`
- First-party requests that look like API traffic are boosted to a floor of `0.85`

The model retrains on a small built-in labelled corpus every time the tool starts. There's no training step and no model file — startup costs a second or two.

**That 0.85 boost is worth knowing about.** Because it keys on "first-party host + XHR," it can promote a site's own telemetry endpoint into `backend_apis`. Scanning `https://dummyjson.com/` — the built-in default — is a good example: the top result is `dummyjson.com/cdn-cgi/rum?`, which is Cloudflare's monitoring beacon, not an API worth calling. When a result looks surprising, check `all_requests` and confirm the endpoint returns something useful before building on it.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'backend_finder'` right after a successful install**

On macOS, if your virtualenv directories carry the Finder "hidden" flag, every file created inside them inherits it — including the `.pth` file that makes an editable install work. Python 3.13+ silently skips hidden `.pth` files, so the install completes but does nothing. Clear the flag and reinstall:

```bash
chflags -R nohidden .venv && pip install -e .
```

You can confirm it's fixed with `ls -lO .venv/lib/python*/site-packages/*.pth` — the flags column should read `-`, not `hidden`.

**The scan finds nothing**

Either the site renders server-side and genuinely has no client-side API, or its calls fire after the tool stops watching. Run with `--no-headless -v` to watch it happen, and lower `-t` to see near-misses.

**`Executable doesn't exist` for a browser**

Normally handled automatically. To install by hand:

```bash
playwright install chromium
```

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
