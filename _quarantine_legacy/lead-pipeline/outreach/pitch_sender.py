# Personalized Email Pitch Sender
# Uses SMTP to send cold outreach emails
import smtplib
import time
import json
import os
import sys
from email.message import EmailMessage
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, FROM_NAME, BCC

def load_leads(filename: str = "leads.json") -> list:
    """Load leads from JSON file."""
    with open(filename) as f:
        return json.load(f)

def generate_pitch(lead: dict) -> tuple:
    """Generate personalized pitch for a lead.
    
    Returns: (subject, body)
    Override this function for your own business context.
    """
    name = lead.get("name", "there")
    city = lead.get("city", "your area")
    
    subject = f"Quick question about {name}"
    
    body = f"""Hi there,

I came across {name} in {city} and was impressed by what you're doing.

We build modern websites and AI automation tools for businesses — think: fast websites, lead capture systems, and SEO that actually works.

Would a quick 10-minute chat this week make sense? No pressure — just exploring if there's a fit.

Best,
{FROM_NAME}
{FROM_EMAIL}
https://aiinvention.tech"""
    
    return subject, body

def send_pitch(lead: dict) -> bool:
    """Send personalized email pitch to a lead."""
    
    if not lead.get("email"):
        return False
    
    subject, body = generate_pitch(lead)
    
    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = lead["email"]
    msg["Subject"] = subject
    msg["Bcc"] = BCC  # Track sent emails in your inbox
    msg.set_content(body)
    
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        print(f"  ✅ Sent to: {lead['email']}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {lead['email']} — {e}")
        return False

if __name__ == "__main__":
    leads = load_leads("leads.json")
    
    # Filter: only leads with email
    email_leads = [l for l in leads if l.get("email")]
    print(f"📧 Leads with email: {len(email_leads)}/{len(leads)}")
    
    if not email_leads:
        print("⚠️  No leads have emails. Run the scraper first or add emails manually.")
        sys.exit(1)
    
    # Load already-pitched emails
    pitched_file = "pitched.json"
    if os.path.exists(pitched_file):
        with open(pitched_file) as f:
            pitched = set(json.load(f))
    else:
        pitched = set()
    
    # Send pitches (rate limited: 1 every 3 seconds)
    sent, failed = 0, 0
    for lead in email_leads:
        if lead["email"] in pitched:
            continue
        
        if send_pitch(lead):
            pitched.add(lead["email"])
            sent += 1
        else:
            failed += 1
        
        time.sleep(3)  # Avoid spam detection
    
    # Save pitched tracker
    with open(pitched_file, "w") as f:
        json.dump(list(pitched), f)
    
    print(f"\n✅ Sent: {sent} | ❌ Failed: {failed} | 📊 Total Pitched: {len(pitched)}")
