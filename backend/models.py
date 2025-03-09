from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field


class Requirements(TypedDict):
    location: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[float] = None
    max_bathrooms: Optional[float] = None


class SearchUrl(BaseModel):
    url: str = Field(description="URL for the Craigslist apartment search page")


class ListingUrl(BaseModel):
    url: str = Field(description="URL for a single apartment listing")


class SearchResults(BaseModel):
    listings: List[ListingUrl] = Field(
        default_factory=list, description="List of apartment listing URLs"
    )


class ListingDetails(BaseModel):
    title: str = Field(description="title of the listing")
    price: str= Field(description="a dollar string for the price of the apartment for example $3,000 or $3000")
    location: str = Field(description="location of the apartment")
    address: Optional[str] = Field(
        None, description="approximate address of the apartment"
    )
    url: str = Field(description="url of the listing")
    bedrooms: int = Field(description="number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="number of bathrooms")
    description: str = Field(description="description of the apartment")
    images: List[str] = Field(
        default_factory=list, description="urls of listing images"
    )


class GeocodingQuery(BaseModel):
    search_text: str = Field(
        description="The main search text to geocode (address, place name, etc.)"
    )
    proximity_point: Optional[List[float]] = Field(
        None,
        description="Optional [longitude, latitude] point to bias results toward",
    )
    country: Optional[List[str]] = Field(
        None,
        description="Optional list of ISO 3166 alpha 2 country codes to limit results",
    )
    types: Optional[List[str]] = Field(
        None,
        description="Optional list of feature types to limit results (address, poi, etc.)",
    )
    limit: Optional[int] = Field(description="Maximum number of results to return")
    autocomplete: Optional[bool] = Field(
        description="Whether to use autocomplete/fuzzy matching"
    )


class GeocodedResult(BaseModel):
    listing_details: ListingDetails
    coordinates: List[float]


class ApartmentFinderState(TypedDict):
    user_description: str
    requirements: Optional[Requirements] = None
    search_results: Optional[SearchResults] = None
    geocoded_listings: Optional[List[GeocodedResult]] = None
