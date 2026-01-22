import asyncio
import aiohttp
import random
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
from whoosh.index import open_dir
import redis
import time

INDEX_DIR = "newt_index"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
]

BLOCKED_DOMAINS = [
    "instagram.com", "facebook.com", "tiktok.com",
    "linkedin.com", "twitter.com", "x.com", "youtube.com"
]

TOP_SEEDS = [
    "https://wikipedia.org",
    "https://news.ycombinator.com",
    "https://github.com",
    "https://stackoverflow.com",
    "https://bbc.com",
    "https://nytimes.com",
    "https://reddit.com/r/all"
]

FRONTIER_QUEUE = "url_queue"
SEEN_SET = "seen_urls"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

async def fetch(session, url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        async with session.get(url, headers=headers, timeout=15) as resp:
            if resp.status != 200:
                return None
            raw = await resp.read()
            return raw.decode("utf-8", errors="ignore")
    except:
        return None

def extract_links(base, soup):
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        href, _ = urldefrag(href)
        if href.startswith("http"):
            links.append(href)
    return links

async def worker(name, session, writer):
    while True:
        url = r.lpop(FRONTIER_QUEUE)

        if not url:
            await asyncio.sleep(0.2)
            continue

        if any(bad in url for bad in BLOCKED_DOMAINS):
            continue

        if r.sismember(SEEN_SET, url):
            continue

        print(f"[{name}] Crawling {url}")

        html = await fetch(session, url)
        if not html:
            continue

        r.sadd(SEEN_SET, url)

        try:
            soup = BeautifulSoup(html, "lxml")
        except:
            soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script","style","nav","footer","header","aside","form"]):
            tag.decompose()

        title = soup.title.get_text() if soup.title else url
        text = soup.get_text(" ", strip=True)
        if len(text) > 15000:
            text = text[:15000]

        writer.update_document(url=url, title=title, content=text)

        for link in extract_links(url, soup)[:40]:
            if not r.sismember(SEEN_SET, link):
                r.rpush(FRONTIER_QUEUE, link)

async def reseed_loop():
    while True:
        for url in TOP_SEEDS:
            if not r.sismember(SEEN_SET, url):
                r.rpush(FRONTIER_QUEUE, url)
        print("🌱 Reseeded top hubs")
        await asyncio.sleep(1800)

async def main():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=100)

    ix = open_dir(INDEX_DIR)
    writer = ix.writer(limitmb=512)

    async with aiohttp.ClientSession(connector=connector) as session:

        async def commit_loop():
            nonlocal writer
            while True:
                await asyncio.sleep(5)
                writer.commit()
                writer = ix.writer(limitmb=512)
                print("💾 Index committed")

        workers = [worker(f"W{i}", session, writer) for i in range(25)]

        await asyncio.gather(
            commit_loop(),
            reseed_loop(),
            *workers
        )

if __name__ == "__main__":
    asyncio.run(main())
