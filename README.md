# 🏠 craigslist agent 🤖

- leverages `browser-use` for web navigation and interaction with Craigslist
- built using `langgraph` to orchestrate an agentic workflow


## demo

<video width="100%" controls>
  <source src="cl-agent-demo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

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
