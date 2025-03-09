from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import uvicorn

from graph import apartment_finder_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    description: str
    planner: str
    executor: str
    headless_mode: bool
    max_listings: int = 10


async def stream_search_results(request: SearchRequest):
    graph = apartment_finder_graph(
        executor_model=request.executor,
        planner_model=request.planner,
        headless_mode=request.headless_mode,
        max_listings=request.max_listings,
    )

    # Initial status message
    yield f"data: {json.dumps({'type': 'status', 'message': '🏠 gathering requirements...'})}\n\n"

    # Set to track which status messages have been sent
    sent_messages = set()

    async for chunk in graph.astream(
        {"user_description": request.description}, stream_mode="values"
    ):
        # Process requirements
        if "requirements" in chunk and "requirements" not in sent_messages:
            sent_messages.add("requirements")
            yield f"data: {json.dumps({'type': 'status', 'message': '🔍 browsing craigslist...'})}\n\n"

        # Process search results
        if (
            "search_results" in chunk
            and hasattr(chunk["search_results"], "listings")
            and "search_results" not in sent_messages
        ):
            sent_messages.add("search_results")
            yield f"data: {json.dumps({'type': 'status', 'message': f'📋 inspecting listings...'})}\n\n"

            listing_urls = []
            for listing in chunk["search_results"].listings:
                if hasattr(listing, "url"):
                    listing_urls.append(listing.url)
                elif hasattr(listing, "model_dump"):
                    listing_data = listing.model_dump()
                    if "url" in listing_data:
                        listing_urls.append(listing_data["url"])

            yield f"data: {json.dumps({'type': 'search_results', 'count': len(chunk["search_results"].listings), 'urls': listing_urls})}\n\n"

        # Process geocoded listings
        if (
            "geocoded_listings" in chunk
            and chunk["geocoded_listings"]
            and "geocoded_listings" not in sent_messages
        ):
            sent_messages.add("geocoded_listings")
            yield f"data: {json.dumps({'type': 'status', 'message': f'🏢 mapping listings...'})}\n\n"

            listings_data = []
            for listing in chunk["geocoded_listings"]:
                if hasattr(listing, "model_dump"):
                    listings_data.append(listing.model_dump())
                else:
                    listings_data.append(vars(listing))

            yield f"data: {json.dumps({'type': 'listings', 'data': listings_data})}\n\n"

        await asyncio.sleep(0.05)

    yield f"data: {json.dumps({'type': 'complete', 'message': '✅ search completed successfully!'})}\n\n"


@app.post("/api/search/stream")
async def stream_search(request: SearchRequest):
    return StreamingResponse(
        stream_search_results(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
