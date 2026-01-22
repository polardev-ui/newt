import os
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from whoosh.index import open_dir, exists_in
from whoosh.qparser import QueryParser

from crawler_api import scout_and_index

app = FastAPI()

INDEX_DIR = "newt_index"
templates = Jinja2Templates(directory="templates")

def search_local_index(query_str):
    if not os.path.exists(INDEX_DIR) or not exists_in(INDEX_DIR):
        return []
    
    ix = open_dir(INDEX_DIR)
    results_list = []
    
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(query_str)
        results = searcher.search(query, limit=10)
        
        for hit in results:
            results_list.append({
                "title": hit.get("title", "No Title"),
                "url": hit.get("url", "#"),
                "snippet": hit.get("content", "")[:200] + "..."
            })
    return results_list

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str):
    await scout_and_index(q)
    
    local_results = search_local_index(q)
    
    status_msg = f"Newt just indexed the web for '{q}'."

    return templates.TemplateResponse("results.html", {
        "request": request,
        "query": q,
        "results": local_results,
        "status": status_msg
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)