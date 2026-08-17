# Scraper Configuration
# Copy this file to config.py and fill in your values

# Your Apify API key (free tier: $5/month)
# Get it from: https://console.apify.com/account/integrations
APIFY_API_KEY = "apify_api_YOUR_KEY_HERE"

# What businesses to search for
SEARCH_QUERIES = [
    "restaurants",
    "cafes",
    "hotels",
    "real estate agents",
    "dental clinics"
]

# Cities to target
TARGET_CITIES = [
    "Kuala Lumpur",
    "Singapore",
    "Jakarta"
]

# Max results per search
MAX_RESULTS = 20
