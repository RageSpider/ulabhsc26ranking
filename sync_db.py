import os
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# --- CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TARGET_DIR = Path("./students")

# --- VALIDATION ---
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env file.")
    exit(1)

print("🔌 Connecting to Supabase...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

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
    content = file_path.read_text(encoding="utf-8")
    file_name = file_path.name
    
    # Extract Roll from filename (e.g., "119.html" -> 119)
    roll_str = file_path.stem # "119"
    
    try:
        roll = int(roll_str)
    except ValueError:
        # print(f"⚠️  Skipping {file_name}: Filename is not a number.")
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
        # print(f"⚠️  Skipping {file_name}: Roll {roll} is out of defined ranges.")
        return

    # --- EXTRACT METADATA (REGEX) ---
    
    # Extract Name (between <h1... > ... </h1>)
    name_match = re.search(r'<h1[^>]*>([\s\S]*?)<\/h1>', content, re.IGNORECASE)
    
    name = f"Student {roll}"
    if name_match:
        raw_name = name_match.group(1)
        # Clean up: remove tags, replace <br> with space, trim
        clean_name = re.sub(r'<br\s*\/?>', ' ', raw_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'<[^>]+>', '', clean_name)
        name = " ".join(clean_name.split())

    # Extract Image URL
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    
    image_url = ""
    if img_match:
        # Remove "../" to make it relative to root
        image_url = img_match.group(1).replace("../", "")

    # Construct Public URL
    page_url = f"https://{url_prefix}.netlify.app/students/{file_name}"

    # --- UPSERT TO SUPABASE ---
    print(f"   Processing: {roll} ({section}) - {name}", end=" ")

    data = {
        "roll": roll_str,
        "section": section,
        "name": name,
        "image_url": image_url,
        "page_url": page_url,
    }

    try:
        # Perform Upsert
        supabase.table("entries").upsert(data, on_conflict="roll,section").execute()
        print("[OK]")
    except Exception as e:
        print(f"[FAIL] {e}")

if __name__ == "__main__":
    sync_database()