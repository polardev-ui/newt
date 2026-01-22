import asyncio
import aiohttp
from bs4 import BeautifulSoup
from whoosh.index import open_dir
import os
import ssl
import sqlite3
import sys
import random
from urllib.parse import urljoin

# --- CRITICAL FIXES FOR LARGE SITES ---
# 1. Increase Python's internal limits
sys.setrecursionlimit(25000) 

# CONFIG
INDEX_DIR = "newt_index"
DB_PATH = "frontier.db"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS queue (url TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

async def perpetual_crawl():
    init_db()
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10) # Limits concurrent connections
    
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("SELECT url FROM queue LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                print("📭 Queue empty. Sleeping...")
                conn.close()
                await asyncio.sleep(10)
                continue
            
            url = row[0]
            conn.execute("DELETE FROM queue WHERE url = ?", (url,))
            conn.commit()
            conn.close()

            headers = {"User-Agent": random.choice(USER_AGENTS)}

            try:
                print(f"🦎 Newt is eating: {url}")
                async with session.get(url, headers=headers, timeout=20) as resp:
                    if resp.status != 200:
                        print(f"🚫 Denied ({resp.status}): {url}")
                        continue
                    
                    # We use .read() and decode to handle potentially broken encodings
                    content_raw = await resp.read()
                    html = content_raw.decode('utf-8', errors='ignore')
                    
                    # --- THE WIKIPEDIA FIX: Use 'lxml' if possible, else 'html.parser' ---
                    # We use a try/except specifically for the Soup creation
                    try:
                        soup = BeautifulSoup(html, 'lxml')
                    except Exception:
                        soup = BeautifulSoup(html, 'html.parser')
                    
                    # IMMEDIATELY remove heavy tags to free memory
                    for tag in ["script", "style", "nav", "footer", "header", "aside", "form"]:
                        for match in soup.find_all(tag):
                            match.decompose()
                    
                    title_tag = soup.find('title')
                    title = title_tag.get_text() if title_tag else url
                    content = soup.get_text(separator=' ', strip=True)[:15000]
                    
                    # Save to Search Index
                    ix = open_dir(INDEX_DIR)
                    # We use a context manager for the writer to ensure it closes properly
                    with ix.writer(limitmb=256) as writer:
                        writer.update_document(url=url, title=title, content=content)
                    
                    # Discover New Links
                    new_links = []
                    for a in soup.find_all('a', href=True):
                        full_link = urljoin(url, a['href'])
                        if full_link.startswith("http") and not any(ext in full_link.lower() for ext in ['.pdf', '.jpg', '.png', '.zip', '.svg']):
                            new_links.append((full_link,))
                    
                    conn = sqlite3.connect(DB_PATH)
                    conn.executemany("INSERT OR IGNORE INTO queue VALUES (?)", new_links[:15])
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ Indexed: {title[:40]}... (Total: {ix.doc_count()})")

            except asyncio.TimeoutError:
                print(f"🕒 Timeout: {url}")
            except Exception as e:
                # This catches the Stack Overflow and lets the crawler move to the next URL
                print(f"⚠️  Skipped {url}: {str(e)[:50]}")

            await asyncio.sleep(1) # Be a polite 1-second crawler

if __name__ == "__main__":
    try:
        asyncio.run(perpetual_crawl())
    except KeyboardInterrupt:
        print("\n🛑 Newt is hibernating.")