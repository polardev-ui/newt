import asyncio
import aiohttp
from bs4 import BeautifulSoup
from whoosh.index import open_dir
import os
import ssl

SERPER_API_KEY = "02796c9f21aeb091c97a96d4a2c1f680956aa2ac"
INDEX_DIR = "newt_index"

async def scout_and_index(query):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    payload = [{"q": query, "num": 10}]
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        try:
            async with session.post('https://google.serper.dev/search', json=payload[0]) as resp:
                data = await resp.json()
                urls = [result['link'] for result in data.get('organic', [])]
                print(f"🔎 Google found {len(urls)} high-quality leads for '{query}'")

                for target_url in urls:
                    try:
                        async with session.get(target_url, timeout=10) as page_resp:
                            html = await page_resp.text()
                            soup = BeautifulSoup(html, 'lxml')
                            
                            for s in soup(["script", "style", "nav", "footer"]): s.decompose()
                            content = soup.get_text(separator=' ', strip=True)[:20000]
                            title = soup.title.string if soup.title else target_url
                            
                            if not os.path.exists(INDEX_DIR):
                                print(f"⚠️ Index directory {INDEX_DIR} not found!")
                                continue

                            ix = open_dir(INDEX_DIR)
                            writer = ix.writer()
                            writer.update_document(url=target_url, title=title, content=content)
                            writer.commit()
                            print(f"✅ Indexed: {title[:50]}...")
                    except Exception as e:
                        print(f"⚠️  Skipped: {target_url} (Error: {e})")
        except Exception as e:
            print(f"❌ Critical error connecting to Serper: {e}")

if __name__ == "__main__":
    topic = input("What should Newt research? ")
    asyncio.run(scout_and_index(topic))