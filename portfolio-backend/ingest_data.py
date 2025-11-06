import requests
import os
import sys

BASE_URL = "http://localhost:8000/api"
PORTFOLIO_DIR = "data/portfolio"

print("\n📚 Ingesting all portfolio files...\n")

if not os.path.exists(PORTFOLIO_DIR):
    print(f"❌ Portfolio directory not found: {PORTFOLIO_DIR}")
    sys.exit(1)

markdown_files = [f for f in os.listdir(PORTFOLIO_DIR) if f.endswith('.md')]

if not markdown_files:
    print(f"❌ No markdown files found in {PORTFOLIO_DIR}")
    sys.exit(1)

print(f"Found {len(markdown_files)} files to ingest:\n")

success_count = 0
error_count = 0

for filename in markdown_files:
    filepath = os.path.join(PORTFOLIO_DIR, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        title = filename.replace('.md', '')
        
        print(f"📄 Ingesting: {title:<30} ", end="", flush=True)
        
        response = requests.post(
            f"{BASE_URL}/ingest",
            json={
                "title": title,
                "source": filename,
                "project_type": "project",
                "content": content
            },
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            chunks = data.get('chunks_created', 0)
            print(f"✅ ({chunks} chunks)")
            success_count += 1
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            print(f"❌ Error: {error_msg}")
            error_count += 1
            
    except Exception as e:
        print(f"❌ Exception: {str(e)[:50]}")
        error_count += 1

print(f"\n{'='*50}")
print(f"✅ Success: {success_count}")
print(f"❌ Failed: {error_count}")
print(f"{'='*50}\n")

if error_count == 0:
    print("🎉 All files ingested successfully!\n")
else:
    print(f"⚠️  {error_count} files failed. Check backend logs.\n")
