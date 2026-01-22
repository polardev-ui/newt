import asyncio
import aiohttp
import sqlite3
import ssl

SERPER_API_KEY = "02796c9f21aeb091c97a96d4a2c1f680956aa2ac"
DB_PATH = "frontier.db"

TOPICS = [
    "Artificial Intelligence", "Space Exploration", "Cooking Recipes", 
    "World History", "Quantum Physics", "Stock Market Trends", 
    "Open Source Software", "Travel Guides", "Health and Fitness",
    "Global News 2026", "Climate Change Solutions", "Architecture",
    "YouTube Content Creation", "Digital Marketing", "Cryptocurrency",
    "Machine Learning", "Virtual Reality", "Renewable Energy", "Philosophy",
    "Psychology", "Education Technology", "Wildlife Conservation", "Film Reviews",
    "Music Production", "Photography Tips", "Gardening", "Personal Finance",
    "Mental Health Awareness", "Sports Analysis", "Automotive Innovations", "Fashion Trends"
]

async def generate_seeds():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    conn = sqlite3.connect(DB_PATH)
    
    async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        for topic in TOPICS:
            print(f"🔎 Seeding topic: {topic}")
            payload = {"q": topic, "num": 20}
            
            async with session.post('https://google.serper.dev/search', json=payload) as resp:
                data = await resp.json()
                urls = [result['link'] for result in data.get('organic', [])]
                
                for url in urls:
                    conn.execute("INSERT OR IGNORE INTO queue VALUES (?)", (url,))
                
                print(f"✅ Added {len(urls)} links for {topic}")
            
            await asyncio.sleep(1) # Be nice to the API
            
    conn.commit()
    conn.close()
    print("\n🚀 Database seeded! You can now run crawler_247.py to start indexing.")

if __name__ == "__main__":
    asyncio.run(generate_seeds())