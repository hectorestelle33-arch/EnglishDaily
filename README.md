# Daily English World Briefing

A local Streamlit MVP for reading high-quality English world news with DeepSeek-assisted selection, summaries, and language-learning notes.

## Project Structure

```text
EnglishDaily/
  app.py
  requirements.txt
  .env.example
  .gitignore
  README.md
  english_daily/
    ai.py
    briefing.py
    config.py
    export.py
    fetcher.py
    models.py
    sources.py
    storage.py
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=disabled
DEEPSEEK_TIMEOUT=90
```

## Run

```powershell
streamlit run app.py
```

## MVP Notes

- News candidates come from RSS feeds and open feeds only.
- The app does not bypass paywalls and does not scrape login-only full text.
- DeepSeek is used to score, filter, summarize, and generate language-learning material.
- Daily output is saved under `data/`; exports are generated from the Streamlit download button.
