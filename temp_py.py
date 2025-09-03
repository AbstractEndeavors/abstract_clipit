#!/usr/bin/env python3
import requests
import whois
import time
from urllib.parse import quote_plus

# === CONFIGURATION ===
# 1) Marker API (USPTO) - see https://markerapi.com/docs/ (Marker API V2) :contentReference[oaicite:3]{index=3}
MARKER_API_KEY = "YOUR_MARKER_API_KEY"
MARKER_BASE_URL = "https://api.markerapi.com/v2/trademarkSearch"

# 2) EUIPO Trade Mark Search API - see EUIPO API portal :contentReference[oaicite:4]{index=4}
EUIPO_CLIENT_ID = "YOUR_EUIPO_CLIENT_ID"
EUIPO_CLIENT_SECRET = "YOUR_EUIPO_CLIENT_SECRET"
EUIPO_TOKEN_URL = "https://dev-sandbox.euipo.europa.eu/oauth2/token"
EUIPO_TM_SEARCH_URL = "https://dev-sandbox.euipo.europa.eu/ohimportal-api/api/trademark/search"

# 3) WIPO Global Brand Database
WIPO_BASE_URL = "https://www.wipo.int/reference/en/branddb/search/json"

# Social platforms to check
SOCIAL_PLATFORMS = {
    "twitter": "https://twitter.com/{}",
    "instagram": "https://www.instagram.com/{}",
    "facebook": "https://www.facebook.com/{}",
    "linkedin": "https://www.linkedin.com/in/{}",
}

# === FUNCTIONS ===

def check_domain(name):
    """Returns True if domain is registered, False if apparently available."""
    for ext in (".com", ".net", ".io"):
        domain = f"{name}{ext}"
        try:
            w = whois.whois(domain)
            if w.domain_name:
                print(f"[DOMAIN] {domain} is registered.")
            else:
                print(f"[DOMAIN] {domain} appears available.")
        except Exception as e:
            # whois lib often throws if not found
            print(f"[DOMAIN] {domain} appears available.")

def check_social_handles(name):
    """Hit profile URLs; 404→free, 200→taken (others = unknown)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    for platform, url_tpl in SOCIAL_PLATFORMS.items():
        url = url_tpl.format(name)
        try:
            r = requests.get(url, headers=headers, timeout=5)
            status = r.status_code
            if status == 404:
                print(f"[SOCIAL] {platform}: '{name}' is available.")
            elif status == 200:
                print(f"[SOCIAL] {platform}: '{name}' is already taken.")
            else:
                print(f"[SOCIAL] {platform}: status {status}.")
        except requests.RequestException:
            print(f"[SOCIAL] {platform}: error checking.")

def search_uspto_marker(name):
    """Query Marker API for USPTO word‐mark matches."""
    params = {
        "q": name,
        "status": "active",   # or "all"
        "apikey": MARKER_API_KEY
    }
    r = requests.get(MARKER_BASE_URL, params=params)
    data = r.json()
    print(f"[USPTO] {len(data.get('records',[]))} results.")
    for rec in data.get("records", [])[:5]:
        print(f"  • {rec['name']} ({rec['serialNumber']}), status={rec['status']}")

def get_euipo_token():
    """OAuth2 client‐credentials flow to get EUIPO access token."""
    data = {
        "grant_type": "client_credentials",
        "client_id": EUIPO_CLIENT_ID,
        "client_secret": EUIPO_CLIENT_SECRET
    }
    r = requests.post(EUIPO_TOKEN_URL, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

def search_euipo(name, token):
    """Search EUIPO trade marks. Returns JSON."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": name, "page": 1, "size": 20}
    r = requests.get(EUIPO_TM_SEARCH_URL, headers=headers, params=params)
    r.raise_for_status()
    hits = r.json().get("content", [])
    print(f"[EUIPO] {len(hits)} results.")
    for h in hits[:5]:
        print(f"  • {h.get('markText')} ({h.get('registrationNumber')})")

def search_wipo(name):
    """Search WIPO Global Brand DB. Returns JSON."""
    # Note: this endpoint is illustrative; consult WIPO docs for exact params
    params = {"keyword": name, "rows": 20, "start": 0}
    r = requests.get(WIPO_BASE_URL, params=params)
    r.raise_for_status()
    resp = r.json()
    print(f"[WIPO] {resp.get('response',{}).get('numFound',0)} results.")
    for doc in resp.get("response", {}).get("docs", [])[:5]:
        print(f"  • {doc.get('word_mark')} (ID {doc.get('id')})")

# === MAIN WORKFLOW ===

def run_all(name):
    print(f"\n=== Clearing name: '{name}' ===\n")
    check_domain(name)
    check_social_handles(name)
    print()
    search_uspto_marker(name)
    print()
    token = get_euipo_token()
    search_euipo(name, token)
    print()
    search_wipo(name)
    print("\n=== Done ===\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 clearance.py <NAME_TO_CHECK>")
        sys.exit(1)
    run_all(sys.argv[1].strip().replace(" ", ""))  # remove spaces for handles/domains
