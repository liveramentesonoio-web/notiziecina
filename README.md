# Italy Chinese News Monitor

A local Mac app for monitoring Italian RSS feeds and surfacing news related to Chinese communities, especially crime, enforcement, immigration, labor exploitation, and other high-attention public-interest stories.

## Features

- Pulls official RSS feeds from:
  - Notizie di Prato
  - La Nazione Prato
  - Corriere Milano
  - Corriere Roma
  - ANSA Toscana
  - ANSA Lombardia
  - ANSA China
- Stores articles locally in SQLite
- Scores articles by:
  - Chinese-community relevance
  - Crime / enforcement / migration / labor signals
  - General public attention signals
- Extracts preview images from feed metadata or article pages
- Provides a local Streamlit UI for filtering and review
- Supports in-page Chinese translation with DeepSeek when `DEEPSEEK_API_KEY` is configured
- Prepares the stored data for later OpenAI summarization and rewriting

## Quick start

```bash
cd /Users/li/Documents/codex/italy-chinese-news-monitor
uv venv
source .venv/bin/activate
uv pip install -e .
streamlit run app.py
```

The app will open in your browser. Use the sidebar button to fetch the latest feed items.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and push this project.
2. In Streamlit Community Cloud, choose that repository and set the main file to `app.py`.
3. In the app settings, add secrets:

```toml
DEEPSEEK_API_KEY = "your_deepseek_api_key"
DEEPSEEK_TRANSLATION_MODEL = "deepseek-chat"
```

Important:

- `data.db` is intentionally not committed, so cloud deployments will start with an empty database.
- Streamlit Community Cloud is suitable for demo use, but not ideal for long-term persistent local data accumulation.

## In-page Chinese translation

If you want translated Chinese content to appear directly inside your own app page, set:

```bash
export DEEPSEEK_API_KEY="your_api_key"
```

Optional:

```bash
export DEEPSEEK_TRANSLATION_MODEL="deepseek-chat"
```

## Project structure

- `app.py`: local UI
- `news_monitor/config.py`: feed sources and scoring keywords
- `news_monitor/fetcher.py`: RSS + article extraction logic
- `news_monitor/database.py`: SQLite persistence
- `news_monitor/scoring.py`: relevance and traffic-oriented scoring

## Future OpenAI integration

Each saved article already has fields suitable for a later enrichment step:

- `title`
- `summary`
- `content_text`
- `image_url`
- `source_name`
- `score`
- `matched_keywords`

Next phase can add:

- Chinese-language summaries
- rewritten titles for broader audience appeal
- structured labels
- daily digest generation
