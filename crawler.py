import httpx
import os
import time
import random
from bs4 import BeautifulSoup
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID
from urllib.parse import urljoin

# --- Standard Schema ---
schema = Schema(url=ID(stored=True, unique=True), title=TEXT(stored=True), content=TEXT(stored=True))

def get_index():
    if not os.path.exists("newt_index"): os.mkdir("newt_index")
    if not exists_in("newt_index"): return create_in("newt_index", schema)
    return open_dir("newt_index")

def index_page(url, title, content):
    """Safely opens and closes the index for every single page."""
    ix = get_index()
    writer = ix.writer()
    writer.update_document(url=url, title=title, content=content)
    writer.commit() # This clears the memory after every page

def run_crawler(seed_url):
    queue = [seed_url]
    visited = set()
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"}

    with httpx.Client(headers=headers, follow_redirects=True, timeout=20) as client:
        while queue:
            url = queue.pop(0)
            if url in visited: continue
            visited.add(url)

            try:
                print(f"🦎 Newt is exploring: {url}")
                time.sleep(random.uniform(1, 2)) # Faster but safe
                
                resp = client.get(url)
                if resp.status_code != 200: continue

                soup = BeautifulSoup(resp.text, 'html.parser')
                title = soup.title.string if soup.title else url
                
                # Strip junk to save memory
                for tag in soup(["script", "style", "nav", "footer"]): tag.decompose()
                text = soup.get_text(separator=' ', strip=True)

                # Save to Index
                index_page(url, title, text)
                print(f"✅ Saved: {title}")

                # Find links
                for a in soup.find_all('a', href=True):
                    link = urljoin(url, a['href'])
                    if link.startswith("http") and link not in visited:
                        queue.append(link)
                
                print(f"📈 Total Index: {len(visited)} pages. Next in line: {len(queue)}")

            except Exception as e:
                print(f"⚠️  Skipped {url} due to error.") # Don't print the whole error to save stack space

if __name__ == "__main__":
    run_crawler("https://example.com")