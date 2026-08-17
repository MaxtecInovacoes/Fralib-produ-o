# Google Maps Lead Scraper using Apify
# Documentation: https://docs.apify.com/platform/actors/running
import requests
import json
import time
from config import APIFY_API_KEY, SEARCH_QUERIES, TARGET_CITIES

ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # crawler-google-places by Compass
BASE_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"

def scrape_leads(query: str, city: str, max_results: int = 20) -> list:
    """Scrape Google Maps for businesses matching query in city."""
    
    run_input = {
        "searchStringsArray": [f"{query} in {city}"],
        "maxCrawledPlacesPerSearch": max_results,
        "language": "en",
        "includeWebResults": True,
        "includePhone": True,
        "includeWebsite": True,
        "includeOpeningHours": False,
        "includePopularTimes": False
    }
    
    # Start the actor run
    headers = {"Content-Type": "application/json"}
    params = {"token": APIFY_API_KEY}
    
    resp = requests.post(BASE_URL, json=run_input, headers=headers, params=params)
    if resp.status_code != 201:
        print(f"Error starting run: {resp.status_code} {resp.text[:200]}")
        return []
    
    run_data = resp.json()
    run_id = run_data["data"]["id"]
    print(f"Run started: {run_id}")
    
    # Wait for completion (poll every 5s, max 2 min)
    dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_KEY}&format=json"
    
    for _ in range(24):  # 2 minutes max
        time.sleep(5)
        resp = requests.get(dataset_url)
        if resp.status_code == 200:
            items = resp.json()
            if items:
                results = []
                for item in items:
                    results.append({
                        "name": item.get("title", ""),
                        "phone": item.get("phone", ""),
                        "website": item.get("website", ""),
                        "address": item.get("address", ""),
                        "city": item.get("city", city),
                        "category": item.get("categoryName", ""),
                        "rating": item.get("totalScore", ""),
                        "reviews": item.get("reviewsCount", 0),
                        "maps_link": item.get("url", "")
                    })
                return results
        print(f"Waiting... {_ * 5}s")
    
    print("Timeout: run did not complete in 2 minutes")
    return []

def save_to_json(leads: list, filename: str = "leads.json"):
    """Save leads to JSON file."""
    with open(filename, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"Saved {len(leads)} leads to {filename}")

if __name__ == "__main__":
    all_leads = []
    for query in SEARCH_QUERIES:
        for city in TARGET_CITIES:
            print(f"\n🔍 Searching: {query} in {city}")
            leads = scrape_leads(query, city)
            print(f"   Found: {len(leads)} leads")
            all_leads.extend(leads)
    
    # Deduplicate by name
    seen = set()
    unique = []
    for lead in all_leads:
        if lead["name"] not in seen:
            seen.add(lead["name"])
            unique.append(lead)
    
    print(f"\n✅ Total unique leads: {len(unique)}")
    save_to_json(unique, "leads.json")
