# Newt Search

A fast, privacy-focused, open-source web search engine built with Python. Newt uses distributed crawling and real-time indexing to deliver search results from across the web.

## Features

- **🔒 Privacy-First**: No tracking, no data collection, no ads
- **⚡ Lightning Fast**: Asynchronous crawling with 25+ concurrent workers
- **🌍 Autonomous**: Self-expanding index that discovers new content automatically
- **🎨 Modern UI**: Clean, professional interface with dark mode and smooth animations
- **🔄 Real-Time**: Live indexing with Redis queue management and Whoosh full-text search

## Architecture

Newt is built on a three-layer architecture:

### 1. **The Crawler** (`crawler.py`)
- **Redis Queue System**: Manages URL frontier with atomic operations
- **25 Async Workers**: Concurrent crawling using `aiohttp` and `asyncio`
- **Smart Filtering**: Blocks social media domains, deduplicates URLs
- **Auto-Reseed**: Periodically re-queues top-tier domains (Wikipedia, HN, GitHub, etc.)
- **Continuous Indexing**: Commits to Whoosh index every 5 seconds

### 2. **The Search API** (`crawler_api.py`)
- **Serper Integration**: Fetches high-quality results from Google for new queries
- **On-Demand Indexing**: When users search, Newt fetches and indexes top results
- **Real-Time Updates**: New content is immediately searchable

### 3. **The Web Interface** (`main.py`)
- **FastAPI Backend**: Serves search results via Whoosh query parser
- **Jinja2 Templates**: Renders beautiful search pages
  - `index.html`: Landing page with animated gradient background
  - `results.html`: Sticky header, result cards with favicons, hover effects
- **Professional Design**: Modern dark theme with smooth animations

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Uvicorn |
| **Search Engine** | Whoosh (full-text indexing) |
| **Queue** | Redis (URL frontier management) |
| **Async I/O** | aiohttp, asyncio |
| **Web Scraping** | BeautifulSoup4, lxml |
| **Frontend** | Jinja2, CSS3 (animations, gradients) |
| **Database** | SQLite (optional frontier.db) |

## Installation

### Prerequisites
```bash
pip install fastapi uvicorn whoosh redis aiohttp beautifulsoup4 lxml
```

### Start Redis
```bash
redis-server
```

Or using Docker:
```bash
docker-compose up -d
```

## Quick Start

### 1. **Seed the Index**
Populate Redis with 300+ high-quality seed URLs:
```bash
python seed.py
```

### 2. **Start the Crawler**
Launch 25 concurrent workers to crawl and index:
```bash
python crawler.py
```

### 3. **Launch the Web Interface**
Start the FastAPI server:
```bash
python main.py
```

Visit `http://localhost:8000` to start searching!

## 📂 Project Structure

```
newt-search/
├── main.py              # FastAPI web server & search interface
├── crawler.py           # Distributed async crawler (25 workers)
├── crawler_api.py       # Serper API integration for guided search
├── seed.py              # 300+ curated seed URLs across all topics
├── api.py               # Legacy JSON-based search API
├── docker-compose.yml   # Redis/Meilisearch container setup
├── frontier.db          # SQLite URL queue (optional)
├── newt_index/          # Whoosh search index directory
└── templates/
    ├── index.html       # Landing page with animated background
    └── results.html     # Search results with favicon integration
```

## Configuration

### Crawler Settings (`crawler.py`)
- `USER_AGENTS`: Rotates between Chrome user agents
- `BLOCKED_DOMAINS`: Filters out social media sites
- `TOP_SEEDS`: Auto-reseeded domains every 30 minutes
- **Workers**: 25 concurrent async workers
- **Commit Interval**: 5 seconds

### Search API (`crawler_api.py`)
- `SERPER_API_KEY`: Google search API integration (Public)
- **Max Results**: 10 URLs per query
- **Timeout**: 10 seconds per page fetch

## UI Features

### Landing Page (`index.html`)
- Animated gradient background with subtle motion
- Logo with gradient icon badge
- Integrated search box with button inside
- Feature highlights (Privacy, Speed, Open Source)
- Fade-in animations on load

### Results Page (`results.html`)
- Sticky search header with logo
- Result cards with dark borders
- Real website favicons (with emoji fallback)
- Staggered fade-in animations
- Hover effects that lift and brighten cards
- Mobile responsive design

## Contributing

Newt is open-source and welcomes contributions! Feel free to:
- Report bugs or suggest features
- Submit pull requests
- Improve documentation
- Add new seed URLs

## 📄 License

MIT License - feel free to use Newt for any project!

## Author

Made with ❤️ by **Josh Clark**
- Website: [wsgpolar.me](https://wsgpolar.me)
- Currently in open beta

---

**Note**: Newt is designed for educational and research purposes. Always respect `robots.txt` and website terms of service when crawling.