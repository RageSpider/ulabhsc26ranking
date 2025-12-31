import os
import re
import requests
from pathlib import Path

# --- 1. MANUAL .ENV READER (No library needed) ---
def load_env():
    env_path = Path(".env")
    if not env_path.exists():
        print("ℹ️  .env file not found.")
        return
    
    print(f"📖 Reading .env from {env_path.resolve()}")
    text = env_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            # Remove quotes if present
            value = value.strip().strip("'").strip('"')
            os.environ[key.strip()] = value

# --- CONFIGURATION ---
load_env()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TARGET_DIR = Path("./students")

# --- VALIDATION ---
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file.")
    exit(1)

# API Headers for Supabase REST Interface
HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates" # This handles the Upsert logic
}

def sync_database():
    print(f"🚀 Scanning folder: {TARGET_DIR.resolve()}")

    if not TARGET_DIR.exists():
        print(f"❌ Error: Directory '{TARGET_DIR}' not found.")
        exit(1)

    count = 0
    
    # Walk through directory
    for file_path in TARGET_DIR.glob("*.html"):
        process_file(file_path)
        count += 1

    print(f"\n✅ Sync Complete! Processed {count} profiles.")

def process_file(file_path: Path):
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Could not read {file_path.name}: {e}")
        return

    file_name = file_path.name
    
    # Extract Roll from filename (e.g., "119.html" -> 119)
    roll_str = file_path.stem # "119"
    
    try:
        roll = int(roll_str)
    except ValueError:
        return

    # --- DETERMINE SECTION ---
    section = "Unknown"
    url_prefix = "students"

    if 1 <= roll <= 99:
        section = "Section A"
        url_prefix = "ulabhsc26asec"
    elif 101 <= roll <= 199:
        section = "Section B"
        url_prefix = "ulabhsc26bsec"
    elif 301 <= roll <= 399:
        section = "Section H"
        url_prefix = "ulabhsc26hsec"
    else:
        return

    # --- EXTRACT METADATA ---
    
    # Extract Name
    name_match = re.search(r'<h1[^>]*>([\s\S]*?)<\/h1>', content, re.IGNORECASE)
    
    name = f"Student {roll}"
    if name_match:
        raw_name = name_match.group(1)
        clean_name = re.sub(r'<br\s*\/?>', ' ', raw_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'<[^>]+>', '', clean_name)
        name = " ".join(clean_name.split())

    # Extract Theme Name (Specific to your request)
    theme_name = ""
    if roll == 119 and section == "Section B":
        theme_name = "Sakura Dreams"

    # Extract Image URL
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    
    image_url = ""
    if img_match:
        # Remove "../" to make it relative to root
        image_url = img_match.group(1).replace("../", "")

    page_url = f"https://{url_prefix}.netlify.app/students/{file_name}"

    # --- UPSERT TO SUPABASE REST API ---
    print(f"   Processing: {roll} ({section}) - {name}", end=" ")

    payload = {
        "roll": roll_str,
        "section": section,
        "name": name,
        "image_url": image_url,
        "page_url": page_url,
        # "theme_name": theme_name # Uncomment if you added this column to Supabase
    }

    # API Endpoint: /rest/v1/entries
    api_url = f"{SUPABASE_URL}/rest/v1/entries"

    try:
        response = requests.post(api_url, headers=HEADERS, json=payload)
        
        if response.status_code in [200, 201, 204]:
            print("[OK]")
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[FAIL] Connection Error: {e}")

if __name__ == "__main__":
    sync_database()