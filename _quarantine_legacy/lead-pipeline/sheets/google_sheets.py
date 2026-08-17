# Google Sheets Integration
# Writes leads to Google Sheets as CRM database
import json
import os
import sys

# IMPORTANT: google packages may be installed outside your venv.
# Add the system dist-packages path if needed:
# sys.path.insert(0, '/usr/local/lib/python3.13/dist-packages')

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("❌ google-auth and google-api-python-client required.")
    print("   pip install google-auth google-api-python-client")
    sys.exit(1)

# CONFIGURATION — Edit these
SHEET_ID = "YOUR_GOOGLE_SHEET_ID"
CREDENTIALS_FILE = "sheets/credentials.json"  # Service account JSON key
SHEET_NAME = "Sheet1"  # Or your custom sheet name

HEADERS = [
    "#", "Date", "Business Name", "Category", "Phone",
    "Email", "Address", "Maps Link", "Rating", "Reviews",
    "Has Website", "Website", "City", "Demo URL", "WhatsApp Link"
]

def get_service():
    """Get authenticated Google Sheets service."""
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def setup_headers(svc):
    """Initialize sheet with headers if empty."""
    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1:O1"
        ).execute()
        if "values" not in result:
            svc.spreadsheets().values().update(
                spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1:O1",
                body={"values": [HEADERS]}, valueInputOption="RAW"
            ).execute()
            print("✅ Headers added")
    except Exception as e:
        print(f"Header setup error: {e}")

def append_leads(svc, leads: list):
    """Append new leads to the sheet."""
    from datetime import date
    
    # Find next empty row
    result = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A:A"
    ).execute()
    next_row = len(result.get("values", [])) + 1
    
    rows = []
    for i, lead in enumerate(leads, 1):
        rows.append([
            next_row + i - 1,
            str(date.today()),
            lead.get("name", ""),
            lead.get("category", ""),
            lead.get("phone", ""),
            lead.get("email", ""),
            lead.get("address", ""),
            lead.get("maps_link", ""),
            lead.get("rating", ""),
            lead.get("reviews", 0),
            "Yes" if lead.get("website") else "No",
            lead.get("website", ""),
            lead.get("city", ""),
            "",  # Demo URL (to be filled after pitching)
            "",  # WhatsApp Link
        ])
    
    range_str = f"{SHEET_NAME}!A{next_row}:O{next_row + len(rows) - 1}"
    svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=range_str,
        body={"values": rows}, valueInputOption="RAW"
    ).execute()
    
    print(f"✅ Appended {len(rows)} leads to sheet")

if __name__ == "__main__":
    # Load leads
    if not os.path.exists("leads.json"):
        print("❌ leads.json not found. Run scraper first.")
        sys.exit(1)
    
    with open("leads.json") as f:
        leads = json.load(f)
    
    # Write to Sheets
    svc = get_service()
    setup_headers(svc)
    append_leads(svc, leads)
