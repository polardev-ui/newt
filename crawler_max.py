import asyncio
import aiohttp
import aiosqlite
import os
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID

# --- Configuration ---
CONCURRENCY = 20  # Lowered to 20 for stability on a MacBook Air
BATCH_SIZE = 1    # Grab one unique URL at a time
INDEX_DIR = "newt_index"
DB_PATH = "frontier.db"

schema = Schema(url=ID(stored=True, unique=True), title=TEXT(stored=True), content=TEXT(stored=True))

async def init_systems():
    if not os.path.exists(INDEX_DIR): os.mkdir(INDEX_DIR)
    if not exists_in(INDEX_DIR): create_in(INDEX_DIR, schema)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS queue (url TEXT PRIMARY KEY, status TEXT DEFAULT 'pending')")
        await db.execute("CREATE TABLE IF NOT EXISTS crawled (url TEXT PRIMARY KEY)")
        # Fresh seeds
        seeds = [('https://en.wikipedia.org/wiki/Main_Page',), ('https://news.ycombinator.com',), ('https://www.bbc.com',)]
        await db.executemany("INSERT OR IGNORE INTO queue (url) VALUES (?)", seeds)
        await db.commit()

async def worker(worker_id, session, ix):
    async with aiosqlite.connect(DB_PATH) as db:
        while True:
            # 1. ATOMIC GET: Find a URL and mark it 'processing' immediately
            async with db.execute("SELECT url FROM queue WHERE status = 'pending' LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if not row:
                    await asyncio.sleep(2)
                    continue
                url = row[0]
                await db.execute("UPDATE queue SET status = 'processing' WHERE url = ?", (url,))
                await db.commit()

            try:
                # Politeness delay: Don't hammer the same site
                await asyncio.sleep(random.uniform(1, 3))
                
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200: 
                        await db.execute("DELETE FROM queue WHERE url = ?", (url,))
                        await db.commit()
                        continue
                    
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    title = soup.title.string if soup.title else url
                    
                    # Clean and Index
                    for s in soup(["script", "style"]): s.decompose()
                    content = soup.get_text(separator=' ', strip=True)[:10000]
                    
                    # Search Index Write
                    writer = ix.writer()
                    writer.update_document(url=url, title=title, content=content)
                    writer.commit()

                    # 2. Link Extraction
                    new_links = []
                    for a in soup.find_all('a', href=True):
                        full = urljoin(url, a['href'])
                        # Only follow new domains to keep the crawl broad!
                        if full.startswith("http") and urlparse(full).netloc != urlparse(url).netloc:
                            new_links.append((full,))
                    
                    # Add new links and clean up
                    await db.executemany("INSERT OR IGNORE INTO queue (url) VALUES (?)", new_links[:5])
                    await db.execute("DELETE FROM queue WHERE url = ?", (url,))
                    await db.execute("INSERT OR IGNORE INTO crawled VALUES (?)", (url,))
                    await db.commit()
                    
                    print(f"✅ Worker {worker_id} finished: {title[:30]}...")

            except Exception:
                await db.execute("UPDATE queue SET status = 'pending' WHERE url = ?", (url,))
                await db.commit()

async def main():
    await init_systems()
    ix = open_dir(INDEX_DIR)
    
    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": "NewtBot/6.0"}) as session:
        tasks = [worker(i, session, ix) for i in range(CONCURRENCY)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())