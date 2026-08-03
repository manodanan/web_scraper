#!/usr/bin/env python3
"""
Backend & API Finder CLI
------------------------
Discovers backend APIs, XHR/Fetch endpoints, GraphQL services,
embedded state data, and API routes for target web applications.

Usage:
  backend-finder https://example.com/ [options]
"""

import sys
import os

# Ensure current script directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import re
import json
import asyncio
import argparse
import subprocess
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

from ml_backend_classifier import MLBackendClassifier

# Terminal ANSI Color Codes
class Colors:
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.GREEN = ""
        cls.CYAN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RESET = ""


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}


def display_manual():
    # Source checkout keeps the page beside this file; an installed package
    # puts it under the environment's share/man/man1 instead.
    candidates = [
        os.path.join(SCRIPT_DIR, "backend_finder.1"),
        os.path.join(sys.prefix, "share", "man", "man1", "backend_finder.1"),
    ]
    for man_path in candidates:
        if os.path.exists(man_path):
            os.system(f"man '{man_path}' 2>/dev/null || cat '{man_path}'")
            sys.exit(0)
    print("Manual page file backend_finder.1 not found.")
    sys.exit(0)


def ensure_chromium_installed(browser_engine="chromium"):
    """Ensures Chromium browser binaries are installed for Playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_type = getattr(p, browser_engine, p.chromium)
            try:
                b = browser_type.launch(headless=True)
                b.close()
                return
            except Exception as e:
                err_str = str(e).lower()
                if "executable doesn't exist" in err_str or "playwright install" in err_str:
                    print(f"    [INFO] {browser_engine.capitalize()} browser missing. Automatically installing {browser_engine}...")
                    subprocess.run([sys.executable, "-m", "playwright", "install", browser_engine], check=True)
                else:
                    raise e
    except Exception as e:
        print(f"    [WARN] Auto-install check note: {e}")


def scan_static_assets(url, classifier, verbose=False):
    """Scans static HTML & JavaScript bundle scripts for API endpoints."""
    print(f"\n[+] [1/2] Scanning static HTML & JavaScript assets...")
    results = {
        "embedded_state": [],
        "discovered_endpoints": [],
        "js_bundles": []
    }
    
    found_endpoints = set()
    try:
        session = requests.Session()
        res = session.get(url, headers=HEADERS, timeout=10)
        res.encoding = res.apparent_encoding or "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # Extract React / Next.js / Nuxt embedded JSON state tags
        for script in soup.find_all("script"):
            script_id = script.get("id", "")
            script_type = script.get("type", "")
            
            if script_id == "__NEXT_DATA__" or "json" in script_type.lower():
                try:
                    data = json.loads(script.string or "")
                    results["embedded_state"].append({
                        "id": script_id or "json_script",
                        "preview": str(data)[:250] + "..."
                    })
                    print(f"    [SUCCESS] Found embedded JSON state ({script_id or 'json'})")
                except Exception:
                    pass
            
            src = script.get("src")
            if src:
                results["js_bundles"].append(urljoin(url, src))

        print(f"    [INFO] Found {len(results['js_bundles'])} JavaScript bundle scripts.")
        
        # Download and regex-scan top JS bundle scripts for API routes
        api_pattern = re.compile(r'["\'`](/(?:api|v[0-9]+|graphql|service|rest|endpoint|query|core)[^"\'\`\s]+)["\'`]', re.IGNORECASE)
        for js_url in results["js_bundles"][:10]:
            try:
                js_res = session.get(js_url, headers=HEADERS, timeout=5)
                if js_res.status_code == 200:
                    matches = api_pattern.findall(js_res.text)
                    for m in matches:
                        found_endpoints.add(m)
            except Exception:
                continue

    except Exception as e:
        print(f"    [WARN] Note on static scanning: {e}")

    # Evaluate each discovered endpoint with ML classifier
    scored_endpoints = []
    for ep in sorted(list(found_endpoints)):
        full_url = urljoin(url, ep)
        score = classifier.predict_score({"url": full_url, "method": "GET", "type": "fetch", "headers": {}})
        scored_endpoints.append({
            "endpoint": ep,
            "full_url": full_url,
            "score": score
        })

    results["discovered_endpoints"] = sorted(scored_endpoints, key=lambda x: x["score"], reverse=True)
    return results


async def scan_live_browser_network(url, classifier, headless=True, verbose=False, browser_engine="chromium"):
    """Intercepts live network calls using Chromium and classifies them with Machine Learning."""
    print(f"\n[+] [2/2] Intercepting Live Network Traffic with {browser_engine.capitalize()}...")
    captured_requests = []
    
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser_type = getattr(p, browser_engine, p.chromium)
            
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ] if browser_engine == "chromium" else []

            try:
                browser = await browser_type.launch(
                    headless=headless,
                    args=launch_args
                )
            except Exception as e:
                err_str = str(e).lower()
                if "executable doesn't exist" in err_str or "playwright install" in err_str:
                    print(f"    [INFO] {browser_engine.capitalize()} binary missing. Installing Chromium...")
                    subprocess.run([sys.executable, "-m", "playwright", "install", browser_engine], check=True)
                    browser = await browser_type.launch(
                        headless=headless,
                        args=launch_args
                    )
                else:
                    raise e

            context = await browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 800}
            )
            
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()

            def handle_request(req):
                res_type = req.resource_type
                req_url = req.url
                
                # Filter binary assets
                if res_type in ["image", "stylesheet", "font", "media"]:
                    return

                req_obj = {
                    "url": req_url,
                    "method": req.method,
                    "type": res_type,
                    "headers": dict(req.headers)
                }

                score = classifier.predict_score(req_obj)
                
                captured_requests.append({
                    "method": req.method,
                    "type": res_type,
                    "url": req_url,
                    "score": score,
                    "headers": dict(req.headers)
                })
                if verbose:
                    print(f"    [TRACE] [{req.method}] ({res_type}) {req_url}")

            page.on("request", handle_request)

            print(f"    [INFO] Navigating {browser_engine.capitalize()} to: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            status_str = f"HTTP {response.status}" if response else "Unknown Status"
            print(f"    [INFO] Initial Response: {status_str}")
            
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollBy(0, 800);")
            await page.wait_for_timeout(2000)

            await browser.close()

    except Exception as e:
        print(f"    [ERROR] Browser network interception error: {e}")

    captured_requests.sort(key=lambda x: x["score"], reverse=True)
    return captured_requests


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Backend & API Finder CLI - Discovers backend APIs and XHR/Fetch endpoints using Chromium and Machine Learning.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="https://dummyjson.com/",
        help="Target web application URL (e.g. https://example.com)"
    )
    parser.add_argument(
        "-u", "--url",
        dest="url_opt",
        help="Target web application URL"
    )
    parser.add_argument(
        "-o", "--output",
        default="backend_report.json",
        help="Path to save output JSON report (default: backend_report.json)"
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.50,
        help="ML confidence score threshold for filtering backend APIs (0.0 to 1.0, default: 0.50)"
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser engine to use for network interception (default: chromium)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chromium browser in visible mode (default: headless)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output logging"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI terminal colors"
    )
    parser.add_argument(
        "--man",
        action="store_true",
        help="Display the Linux manual page (man backend_finder.1)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.man:
        display_manual()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    target_url = args.url_opt or args.target
    if not target_url.startswith("http"):
        target_url = "https://" + target_url

    print(f"\n{Colors.BOLD}=================================================={Colors.RESET}")
    print(f"{Colors.BOLD} BACKEND & API FINDER CLI {Colors.RESET}")
    print(f"{Colors.BOLD}=================================================={Colors.RESET}")
    print(f"Target URL : {Colors.CYAN}{target_url}{Colors.RESET}")
    print(f"Engine     : {args.browser.capitalize()}")
    print(f"Threshold  : {args.threshold * 100:.0f}% ML Confidence")
    print(f"Output File: {args.output}")

    # Ensure Chromium binaries are ready
    ensure_chromium_installed(args.browser)

    # Initialize ML Classifier
    classifier = MLBackendClassifier()
    classifier.set_target_host(target_url)

    # 1. Scan static JS & HTML
    static_results = scan_static_assets(target_url, classifier, verbose=args.verbose)

    # 2. Monitor live browser network calls using Chromium
    live_requests = asyncio.run(
        scan_live_browser_network(
            target_url,
            classifier,
            headless=not args.no_headless,
            verbose=args.verbose,
            browser_engine=args.browser
        )
    )

    # Separate High Confidence Backend APIs from noise
    backend_apis = [r for r in live_requests if r["score"] >= args.threshold]
    third_party_noise = [r for r in live_requests if r["score"] < args.threshold]

    report = {
        "target_url": target_url,
        "browser_engine": args.browser,
        "summary": {
            "total_captured_requests": len(live_requests),
            "backend_apis_count": len(backend_apis),
            "third_party_noise_count": len(third_party_noise),
            "js_endpoints_count": len(static_results["discovered_endpoints"])
        },
        "backend_apis": backend_apis,
        "all_requests": live_requests,
        "js_discovered_endpoints": static_results["discovered_endpoints"],
        "embedded_state": static_results["embedded_state"]
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print Terminal Results Table
    print(f"\n{Colors.BOLD}=================================================={Colors.RESET}")
    print(f"{Colors.BOLD} BACKEND DISCOVERY RESULTS SUMMARY {Colors.RESET}")
    print(f"{Colors.BOLD}=================================================={Colors.RESET}")
    print(f"Backend APIs Identified            : {Colors.GREEN}{len(backend_apis)}{Colors.RESET}")
    print(f"Third-Party & Noise Requests Filtered: {Colors.DIM}{len(third_party_noise)}{Colors.RESET}")

    print(f"\n{Colors.BOLD}Top Identified Backend API Endpoints:{Colors.RESET}")
    print("-" * 88)
    print(f"{'SCORE':<8} | {'METHOD':<6} | {'TYPE':<8} | {'URL'}")
    print("-" * 88)

    display_list = backend_apis if backend_apis else live_requests[:10]
    for req in display_list[:15]:
        score_pct = f"{req['score'] * 100:.1f}%"
        color = Colors.GREEN if req['score'] >= args.threshold else Colors.YELLOW
        method = req['method']
        res_type = req['type']
        url_str = req['url'] if len(req['url']) <= 58 else req['url'][:55] + "..."
        print(f"{color}{score_pct:<8}{Colors.RESET} | {method:<6} | {res_type:<8} | {url_str}")

    if not display_list:
        print("  [INFO] No endpoints captured.")

    if static_results["discovered_endpoints"]:
        print(f"\n{Colors.BOLD}Discovered API Routes in JS Code:{Colors.RESET}")
        print("-" * 88)
        for ep in static_results["discovered_endpoints"][:10]:
            score_pct = f"{ep['score'] * 100:.1f}%"
            print(f"{Colors.CYAN}{score_pct:<8}{Colors.RESET} | {ep['endpoint']}")

    print(f"\n[+] Full report saved to: {Colors.BOLD}{os.path.abspath(args.output)}{Colors.RESET}\n")


if __name__ == "__main__":
    main()
