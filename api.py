from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/search")
async def search(q: str):
    with open('newt_index.json', 'r') as f:
        data = json.load(f)
    
    results = []
    for url, content in data.items():
        if q.lower() in content['text'].lower() or q.lower() in content['title'].lower():
            results.append({"url": url, "title": content['title']})
            
    return {"results": results}