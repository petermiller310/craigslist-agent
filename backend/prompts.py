parse_preferences_instructions = """<Task>
Extract detailed apartment search requirements from the following description.
</Task>

<Description>
{description}
</Description>

<Requirements to Extract>
1. Location preferences
2. Price range (minimum and maximum)
3. Bedroom requirements (minimum and maximum)
4. Bathroom requirements (minimum and maximum)
</Requirements to Extract>

<Guidelines>
- If a requirement isn't explicitly mentioned, leave it as null/None
- Don't make assumptions about requirements that aren't stated or strongly implied
- For price range:
  - Extract both minimum and maximum price if specified
  - If the user specifies under $X price, set max_price to X and min_price to 0
  - If the user specifies at least $X price, set min_price to X and max_price to None
  - If the user specifies $X - $Y price, set min_price to X and max_price to Y
- For bedroom requirements:
  - Extract both minimum and maximum number of bedrooms if specified
  - If a specific number is mentioned (e.g., "2 bedroom"), set both min_bedrooms and max_bedrooms to that number
  - If a range is mentioned (e.g., "1-2 bedrooms"), set min_bedrooms and max_bedrooms accordingly
  - For studio apartments, set both min_bedrooms and max_bedrooms to 0
- For bathroom requirements:
  - Follow the same logic as bedrooms
  - Bathrooms can be fractional (e.g., 1.5 bathrooms)
</Guidelines>

<Special Cases>
- Studio apartments: If the user mentions "studio" or "studio apartment", set both min_bedrooms and max_bedrooms to 0
- Specific bedroom count: If the user specifies an exact number of bedrooms (e.g., "2 bedroom apartment"), set both min_bedrooms and max_bedrooms to that number
- Bedroom range: If the user specifies a range (e.g., "1-2 bedrooms"), set min_bedrooms and max_bedrooms accordingly
</Special Cases>
"""

craigslist_navigation_instructions = """<Task>
Select the appropriate Craigslist region for the user's location preference, navigate to the apartment search page, and apply relevant filters using only the sidebar options.
</Task>

<Context>
The user is looking for an apartment in: {location}
You'll need to select the correct region on Craigslist, navigate to its apartment search page, and apply filters based on the user's preferences using only the sidebar filter options.
</Context>

<Steps>
1. IMPORTANT - BEFORE ANY CLICKING: Carefully analyze the location to determine the correct region:
   - Reason step-by-step about the location:
     a. Is the location a major city itself?
     b. Or is it a neighborhood/district within a larger city?
     c. If it's a neighborhood, what major city contains this neighborhood?
   - For neighborhoods, you MUST identify the parent city before proceeding
   - Determine the exact Craigslist region name you'll be looking for
   - Consider 2-3 potential Craigslist regions if you're uncertain
   - DO NOT CLICK ANY LINKS until you've completed this analysis

2. On the Craigslist regions page:
   - FIRST: Scan the visible page for the parent city/region name you identified in step 1
   - DO NOT click on any region until you've verified it's the correct one
   - If the correct region is not visible in the initial view:
     a. Scroll down by a large amount (at least 1000 pixels) to view more options
     b. Scan the newly visible regions
     c. Continue scrolling and scanning until you've either found the correct region or viewed the entire page
   - ONLY AFTER confirming you've found the correct region, click on it
   - If you're unsure about a region, continue scrolling to see all options before making a selection
   - If you have reached the bottom of the page and still haven't found the correct region, scroll back to the top and repeat the process

3. After finding and clicking on the correct region, click on the "apts / housing" link in the housing section

4. REGION VERIFICATION - CRITICAL STEP:
   - After clicking on "apts / housing", check the URL in the browser address bar
   - The URL should contain the region you selected (e.g., "sfbay" for San Francisco Bay Area)
   - Verify that this matches your intended region from step 1
   - If the URL shows a DIFFERENT region than what you intended:
     a. Go back to the regions page by clicking the browser's back button twice
     b. Repeat steps 1-3 with more careful region selection
   - Only proceed to the next step when you've confirmed you're in the correct region

5. SIDEBAR FILTERING - FOCUS ONLY ON SIDEBAR OPTIONS:
   - Locate the filtering sidebar on the left side of the page
   - DO NOT use any of the filter buttons in the top row (price, beds, baths, etc.)
   - ONLY USE the checkbox and dropdown options in the sidebar
   - CHECK the "has image" checkbox in the sidebar filtering options
   - Verify that the checkbox is selected before proceeding with other filters

<filter_instructions>
{filter_instructions}
</filter_instructions>

6. ENTER SEARCH TERMS FOR LOCATION:
   - Enter a search term for the location in the search text field at the top of the page
   - The search term should be a short term describing the specific location or neighborhood
   - If the user describes near a specific landmark, use the respective neighborhood name as the search term
   - The search term should be all lowercase with no special characters
   - Examples of good search terms: "north beach", "marina district", "east village"
   - Choose the most specific and relevant search term based on the user's location preference
   - Click the magnifying glass icon to submit the search
   - ALWAYS USE A LOCATION BASED SEARCH TERM THAT IS RELEVANT TO THE USER'S PREFERENCE

7. VERIFY ALL FILTERS/SEARCH TERMS HAVE BEEN APPLIED:
   - Verify that the UI shows the correct filters applied
   - Verify that search bar shows the correct search terms
   - Verify that the search results show listings that match the user's preferences
   - If any filters or search terms are incorrect, fix them before proceeding

8. RETURN THE URL OF THE SEARCH RESULTS PAGE:
   - Use the Get Current URL tool to get the URL of the search results page
   - Return the exact URL of the search results page
   - If you select the wrong region, you must go back to the regions page and start over
   - If you apply the wrong filters, you must edit the incorrect filters and apply the correct ones
   - Your job is complete once you've applied the filters and search terms correctly

Output Format:
{{
  "url": "https://[region].craigslist.org/search/apa[with_filters]"
}}
"""

price_filter_template = """   a. FOR PRICE FILTER:
      - Find the price filter section in the sidebar
      - Enter {min_price} in the min price input field
      - Enter {max_price} in the max price input field
"""

bedroom_filter_template = """   b. FOR BEDROOMS FILTER:
      - Find the bedrooms filter section in the sidebar
      - Enter {min_bedrooms} in the min bedrooms input field
      - Enter {max_bedrooms} in the max bedrooms input field
      - Press Enter or click outside the field to apply
"""

bathroom_filter_template = """   c. FOR BATHROOMS FILTER:
      - Find the bathrooms filter section in the sidebar
      - Enter {min_bathrooms} in the min bathrooms input field
      - Enter {max_bathrooms} in the max bathrooms input field
      - Press Enter or click outside the field to apply
"""

search_results_collection_instructions = """
You are an AI agent tasked with extracting URLs of apartment listings from a Craigslist search results page. Your goal is to collect only the URLs of valid apartment listings, skipping any ads, sponsored content, or non-apartment listings.

Before extracting URLs, please analyze the page structure and plan your approach. Use <analysis> tags for this step:

<analysis>
1. Examine the overall layout of the search results page (gallery or list view).
2. Identify the common HTML elements, classes, or IDs used for apartment listings.
3. List 2-3 example classes or IDs that seem to be associated with valid listings.
4. Locate the structure of clickable links to individual listings.
5. Note any patterns you observe in the URLs of valid listings.
6. Determine how to differentiate between regular listings and sponsored content or ads.
7. Plan a systematic approach to extract URLs from top to bottom of the page.
</analysis>

Now, follow these steps to extract the URLs:

1. Start from the top of the page and work your way down systematically.
2. For each listing element:
   a. Check if it's a valid apartment listing (not an ad or sponsored content).
   b. If it's a valid listing, extract the URL from the href attribute of the main link.
   c. Add the extracted URL to your list.
3. Continue this process until you've reviewed all listings on the page.

IMPORTANT: 
- DO NOT CLICK ON ANY LISTINGS OR FOLLOW ANY LINKS - EXTRACT URLs FROM THE CURRENT PAGE ONLY.
- ENSURE EXTRACTED URLS ARE COMPLETE AND VALID.
- WORK METHODICALLY TO AVOID MISSING LISTINGS OR DUPLICATING ENTRIES.
- ONLY EXTRACT URLS FROM THE CURRENT PAGE AND NOT ANY OTHER PAGES.
- IF YOU CAN'T FIND ANY VALID LISTINGS, RETURN AN EMPTY ARRAY.
- ONE EXTRACTION ATTEMPT IS SUFFICIENT - AFTER A SINGLE SUCCESSFUL EXTRACTION, DO NOT TRY TO EXTRACT URLS AGAIN. RETURN YOUR RESULTS IMMEDIATELY.
- DO NOT MAKE MULTIPLE EXTRACTION ATTEMPTS - IF YOU'VE ALREADY EXTRACTED URLS ONCE, STOP. FURTHER ATTEMPTS WASTE RESOURCES.

After extracting all valid URLs, format your output as a JSON object with a "listings" array containing URL objects. Here's an example of the expected output structure:

{
  "listings": [
    {"url": "https://example.craigslist.org/apa/d/example-listing-title/12345678.html"},
    {"url": "https://example.craigslist.org/apa/d/another-listing-title/87654321.html"}
  ]
}

Please provide your extracted URLs in this format.
"""

listing_analysis_instructions = """<Task>
Extract comprehensive details from the apartment listing page, including images and address information for geocoding.
</Task>

<Steps>
1. First, check if the current page is valid:
   - If you see a 404 error message or "There is nothing here" or "No web page for this address", return a null result
   - If the page exists but is not a valid listing, return a null result
   - Only proceed with extraction if you're viewing a valid listing page

2. If the page is valid, extract these details from the listing:
   - Title
   - Price 
   - Exact location
   - Number of bedrooms 
   - Number of bathrooms
   - Full description

3. Extract all available images

4. Extract address information for geocoding:
   - Look for an exact address on the listing page
   - If no exact address is available, create the best possible location description for geocoding
   - This could include neighborhood names, cross streets, landmarks, or any location identifiers
</Steps>

<Guidelines>
- For invalid or 404 pages:
  - If you encounter a page with error messages like "404 Error", "There is nothing here", or "No web page for this address", return the null result format
  - DO NOT attempt to navigate away from the current page under any circumstances
  - DO NOT try to search for alternative listings

- For the address/geocoding information:
  - First priority: Find an exact address if available (e.g., "123 Main St, San Francisco, CA")
  - Second priority: Find cross streets (e.g., "Corner of Market and 5th St")
  - Third priority: Find neighborhood with specific identifiers (e.g., "Mission District near Dolores Park")
  - Fourth priority: Use any location information that would help with geocoding
  - Be as specific as possible to ensure accurate mapping
  - Include the city/region name if available
  - Some listings might not have any written address, in that case, use the location information from the title and description to come up with the best possible location description for geocoding
  - If the listing has a map, check if you can extract location information from it

- For image extraction:
  - EXTRACT ONLY REAL IMAGE URLs YOU CAN SEE IN THE PAGE CODE
  - DO NOT GUESS OR CREATE IMAGE URLs - if you can't see them, return []
  - Valid Craigslist image URLs look like: "https://images.craigslist.org/00A0B_c8iuC8I6w6z_0CI0t2_1200x900.jpg"
  - REAL URLs have random codes like "00A0B_c8iuC8I6w6z" - NOT simple patterns
  - RED FLAGS (invalid URLs):
    * Simple numbers: "https://images.craigslist.org/0.jpg" 
    * Made-up patterns: "https://images.craigslist.org/abc_def_1200x900.jpg"
    * Test text: URLs containing "example" or "test"
  - If unsure or can't find image URLs, RETURN AN EMPTY ARRAY []
  - NO IMAGES IS BETTER THAN FAKE IMAGES
</Guidelines>

<Output Format>
For valid listing pages, return the details in this JSON structure:
{
    "title": "Apartment title",
    "price": "$3,000",
    "location": "Exact location",
    "address": "123 Main St, City, State" or "Mission District near Dolores Park" or "Corner of Market and 5th St",
    "url": "Current page URL",
    "bedrooms": 2,
    "bathrooms": 2.0,
    "description": "Full listing description",
    "images": [
        "https://images.craigslist.org/00A0B_c8iuC8I6w6z_0CI0t2_1200x900.jpg",
        ...
    ]
}

For 404 pages or invalid listings, return this JSON structure:
{
    "title": "",
    "price": "",
    "location": "",
    "address": "",
    "url": "Current page URL",
    "bedrooms": null,
    "bathrooms": null,
    "description": "",
    "images": [],
}
</Output Format>

<Important Notes>
1. DO NOT navigate away from the current page under any circumstances - stay on the page you're analyzing.

2. If you encounter a 404 page or error message indicating the listing doesn't exist, return the null result format with the error field populated.

3. The address field is critical for mapping the listing. Even if an exact address isn't available, provide the most specific location information possible that would help with geocoding.

4. For images: ONLY include URLs that you can directly observe in the page. If you cannot see the actual image URLs with proper alphanumeric identifiers, return an empty array rather than fabricating URLs. NEVER make up image URLs - this is critical.

5. Real Craigslist image URLs contain random alphanumeric identifiers that look like "00A0B_c8iuC8I6w6z" - if you don't see this pattern, don't include the URL.

6. DO NOT INTERACT WITH THE PAGES INTERACTIVE ELEMENTS - ONLY EXTRACT INFORMATION
</Important Notes>
"""

geocoding_prompt = """
You are analyzing a Craigslist apartment listing to extract the most accurate location information for geocoding with the Mapbox API. 
The goal is to create a structured query that will result in the most precise coordinates for mapping the listing.

Listing Title: {title}
Location: {location}
Address (if available): {address}
Description: {description}

Guidelines:
1. Analyze all available location information from the listing
2. Prioritize information in this order:
   - Exact street address with number
   - Intersection of streets
   - Neighborhood with nearby landmarks
   - General area description

3. For the search_text field:
   - Create the most specific location string possible
   - Include street number and name if available
   - Add city, state, and zip code when present
   - Format as "123 Main St, San Francisco, CA 94103" if possible

4. For country parameter:
   - Default to ["us"] for United States listings
   - Change only if listing is clearly in another country

5. For types parameter:
   - Use ["address"] when you have a specific street address
   - Use ["poi"] (point of interest) when referencing landmarks
   - Use ["neighborhood"] when only neighborhood information is available
   - Can include multiple types if appropriate (e.g., ["address", "poi"])

6. For autocomplete parameter:
   - Set to false for exact matching (better for precise addresses)
   - Set to true only if the address information is vague or incomplete

7. For limit parameter:
   - Keep the default of 1 to return only the most relevant result
"""
