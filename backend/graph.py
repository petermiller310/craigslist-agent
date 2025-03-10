import asyncio
import os
import requests
from typing import List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from browser_use import Agent, Browser, BrowserConfig, BrowserContextConfig, Controller, ActionResult

from prompts import (
    parse_preferences_instructions,
    craigslist_navigation_instructions,
    price_filter_template,
    bedroom_filter_template,
    bathroom_filter_template,
    search_results_collection_instructions,
    listing_analysis_instructions,
    geocoding_prompt,
)
from models import (
    ApartmentFinderState,
    Requirements,
    SearchUrl,
    SearchResults,
    ListingDetails,
    GeocodingQuery,
    GeocodedResult,
)

from dotenv import load_dotenv

load_dotenv()

MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN")


def apartment_finder_graph(
    executor_model="gpt-4o-mini",
    planner_model="gpt-4o",
    headless_mode=True,
    max_listings=10,
):
    if executor_model == "claude-3-5-sonnet-latest":
        llm = ChatAnthropic(model=executor_model)
    else:
        llm = ChatOpenAI(model=executor_model)

    if planner_model == "claude-3-5-sonnet-latest":
        planner_llm = ChatAnthropic(model=planner_model)
    else:
        planner_llm = ChatOpenAI(model=planner_model)

    browser_config = BrowserConfig(headless=headless_mode)

    _max_listings = max_listings

    graph = StateGraph(ApartmentFinderState)
    browser_context_config = BrowserContextConfig(allowed_domains=["craigslist.org"])

    async def gather_requirements(
        state: ApartmentFinderState,
    ) -> ApartmentFinderState:
        description = state["user_description"]
        structured_llm = llm.with_structured_output(Requirements)

        requirements = await structured_llm.ainvoke(
            parse_preferences_instructions.format(description=description)
        )

        return {
            **state,
            "requirements": requirements,
        }

    async def browse_craigslist(
        state: ApartmentFinderState,
    ) -> ApartmentFinderState:
        browser = None
        try:
            browser = Browser(config=browser_config)
            requirements = state["requirements"]
            location = requirements["location"]

            filter_parts = []

            if (
                requirements["min_price"] is not None
                or requirements["max_price"] is not None
            ):
                filter_parts.append(
                    price_filter_template.format(
                        min_price=requirements["min_price"] or "",
                        max_price=requirements["max_price"] or "",
                    )
                )

            if (
                requirements["min_bedrooms"] is not None
                or requirements["max_bedrooms"] is not None
            ):
                filter_parts.append(
                    bedroom_filter_template.format(
                        min_bedrooms=requirements["min_bedrooms"] or "",
                        max_bedrooms=requirements["max_bedrooms"] or "",
                    )
                )

            if (
                requirements["min_bathrooms"] is not None
                or requirements["max_bathrooms"] is not None
            ):
                filter_parts.append(
                    bathroom_filter_template.format(
                        min_bathrooms=requirements["min_bathrooms"] or "",
                        max_bathrooms=requirements["max_bathrooms"] or "",
                    )
                )

            filter_instructions = "\n".join(filter_parts)

            async with await browser.new_context(config=browser_context_config) as context:
                search_controller = Controller(output_model=SearchUrl)

                @search_controller.action("Get current URL")
                async def get_current_url(browser: Browser):
                    page = browser.get_current_page()
                    await page.reload()
                    await page.wait_for_load_state("networkidle")
                    current_url = await page.evaluate("window.location.href")
                    return ActionResult(extracted_content=current_url)

                search_agent = Agent(
                    task=craigslist_navigation_instructions.format(
                        location=location, filter_instructions=filter_instructions
                    ),
                    llm=llm,
                    planner_llm=planner_llm,
                    use_vision_for_planner=True,
                    controller=search_controller,
                    use_vision=True,
                    planner_interval=2,
                    initial_actions=[
                        {"go_to_url": {"url": "https://geo.craigslist.org/iso/us"}}
                    ],
                    browser=browser,
                    browser_context=context,
                )

                history = await search_agent.run()
                search_url_result = history.final_result()
                search_url = SearchUrl.model_validate_json(search_url_result)

                extract_search_results_controller = Controller(
                    output_model=SearchResults
                )
                extract_search_results_agent = Agent(
                    task=search_results_collection_instructions,
                    llm=llm,
                    planner_llm=planner_llm,
                    use_vision_for_planner=True,
                    controller=extract_search_results_controller,
                    use_vision=True,
                    planner_interval=2,
                    browser_context=context,
                    browser=browser,
                    initial_actions=[{"go_to_url": {"url": search_url.url}}],
                )

                history = await extract_search_results_agent.run(max_steps=10)
                search_results = SearchResults.model_validate_json(
                    history.final_result()
                )

            return {
                **state,
                "search_results": search_results,
            }
        finally:
            if browser:
                await browser.close()

    async def collect_listing_details(
        state: ApartmentFinderState,
    ) -> ApartmentFinderState:
        browser = None
        try:
            browser = Browser(config=browser_config)

            search_results = state["search_results"]
            geocoded_listings = []

            async def process_listing(listing_url):
                listing_browser = None
                try:
                    listing_browser = Browser(config=browser_config)
                    async with await listing_browser.new_context(config=browser_context_config) as context:
                        extract_listing_details_controller = Controller(
                            output_model=ListingDetails
                        )
                        extract_listing_details_agent = Agent(
                            controller=extract_listing_details_controller,
                            browser_context=context,
                            browser=listing_browser,
                            task=listing_analysis_instructions,
                            llm=llm,
                            use_vision=True,
                            initial_actions=[{"go_to_url": {"url": listing_url.url}}],
                        )

                        history = await extract_listing_details_agent.run(max_steps=10)
                        result_data = history.final_result()
                        listing_details = ListingDetails.model_validate_json(
                            result_data
                        )

                        coordinates = await geocode(listing_details)

                        return GeocodedResult(
                            listing_details=listing_details,
                            coordinates=coordinates,
                        )
                finally:
                    if listing_browser:
                        await listing_browser.close()

            truncated_results = SearchResults(
                listings=search_results.listings[:_max_listings]
            )
            tasks = [
                process_listing(listing_url)
                for listing_url in truncated_results.listings
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            geocoded_listings = [r for r in results if not isinstance(r, Exception)]

            return {
                **state,
                "geocoded_listings": geocoded_listings,
            }
        finally:
            if browser:
                await browser.close()

    async def geocode(listing_details: ListingDetails) -> List[float]:
        default_coords = [0.0, 0.0]

        if not MAPBOX_ACCESS_TOKEN:
            return default_coords

        try:
            geocoding_query = await llm.with_structured_output(
                GeocodingQuery
            ).ainvoke(
                geocoding_prompt.format(
                    title=listing_details.title,
                    location=listing_details.location,
                    address=listing_details.address or "Not provided",
                    description=listing_details.description,
                ),
            )

            base_url = "https://api.mapbox.com/geocoding/v5/mapbox.places"
            query = requests.utils.quote(geocoding_query.search_text)
            request_url = f"{base_url}/{query}.json"
            params = {"access_token": MAPBOX_ACCESS_TOKEN, "limit": 1}

            response = requests.get(request_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "features" in data and data["features"]:
                return data["features"][0]["geometry"]["coordinates"]

        except Exception:
            try:
                fallback_query = listing_details.location
                if fallback_query:
                    base_url = "https://api.mapbox.com/geocoding/v5/mapbox.places"
                    query = requests.utils.quote(fallback_query)
                    request_url = f"{base_url}/{query}.json"
                    params = {"access_token": MAPBOX_ACCESS_TOKEN, "limit": 1}

                    response = requests.get(request_url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if "features" in data and data["features"]:
                        return data["features"][0]["geometry"]["coordinates"]
            except Exception:
                pass

        return default_coords

    graph.add_node("extract_requirements", gather_requirements)
    graph.add_node("search_craigslist", browse_craigslist)
    graph.add_node("extract_listing_details", collect_listing_details)

    graph.set_entry_point("extract_requirements")

    graph.add_edge("extract_requirements", "search_craigslist")
    graph.add_edge("search_craigslist", "extract_listing_details")
    graph.add_edge("extract_listing_details", END)

    return graph.compile()
