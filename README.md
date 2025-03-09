# 🏠 craigslist agent 🤖

- leverages `browser-use` for web navigation and interaction with Craigslist
- built using `langgraph` to orchestrate an agentic workflow

## Setup

create a `.env` file in the backend directory with:

```
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

```
make setup
make start
```
