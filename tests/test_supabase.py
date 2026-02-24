from supabase import create_client
import sys
import os
from dotenv import load_dotenv

# Make sure we load from the root .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print("URL:", url)
print("KEY EXISTS:", bool(key))

if url and key:
    client = create_client(url, key)
    print("Supabase connected ✅")
else:
    print("❌ Missing Supabase credentials")
