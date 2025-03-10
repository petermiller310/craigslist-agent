# 🏠 craigslist agent 🤖

- leverages `browser-use` for web navigation and interaction with Craigslist
- built using `langgraph` to orchestrate an agentic workflow
- note: max listings is the maximum number of listings to look at (i.e. maximum number of browser windows to open if running in non-headless mode)

## demo

![demo](cl-agent-demo-gif.gif)

![demo2](cl-agent-demo-gif-2.gif)

![demo3](cl-agent-demo-gif-3.gif)

## setup

create a `.env` file w/

```
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

```
make setup
make start
```
