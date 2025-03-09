import { useActionData, useSubmit } from "@remix-run/react";
import { useEffect, useRef, useState } from "react";
import type { ActionFunctionArgs } from "@remix-run/node";

type Listing = {
  listing_details: {
    title: string;
    price: number;
    location: string;
    address: string | null;
    url: string;
    bedrooms: number;
    bathrooms: number | null;
    description: string;
    images: string[];
  };
  coordinates: number[];
};

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const description = formData.get("description") as string;
  const planner = formData.get("planner") as string;
  const executor = formData.get("executor") as string;
  const headlessMode = formData.has("headlessMode");
  const maxListingsValue = formData.get("maxListings") as string;

  const errors: { [key: string]: string } = {};

  const maxListings = parseInt(maxListingsValue);
  if (isNaN(maxListings)) {
    errors.maxListings = "Please enter a valid number";
  } else if (maxListings < 1) {
    errors.maxListings = "Must be at least 1";
  } else if (maxListings > 50) {
    errors.maxListings = "Cannot exceed 50";
  }

  if (Object.keys(errors).length > 0) {
    return Response.json({ errors, fields: { description, planner, executor, headlessMode, maxListings } });
  }

  return Response.json({
    searchParams: { description, planner, executor, headlessMode, maxListings }
  });
}

export default function Index() {
  const actionData = useActionData<typeof action>();
  const submit = useSubmit();

  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string[]>([]);
  const [streamingError, setStreamingError] = useState<string | null>(null);
  const [listingUrls, setListingUrls] = useState<string[]>([]);
  const [geocodedListings, setGeocodedListings] = useState<Listing[]>([]);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [expandedListings, setExpandedListings] = useState<{ [key: string]: boolean }>({});
  const [selectedPlanner, setSelectedPlanner] = useState("gpt-4o");
  const [selectedExecutor, setSelectedExecutor] = useState("gpt-4o-mini");
  const [headlessMode, setHeadlessMode] = useState(true);
  const [expandedUrlsPanel, setExpandedUrlsPanel] = useState(false);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSearching) return;

    setStreamStatus([]);
    setStreamingError(null);
    setListingUrls([]);
    setGeocodedListings([]);
    setSelectedListing(null);
    setIsSearching(true);

    const formData = new FormData(event.currentTarget);
    submit(formData, { method: "post", replace: true });
  };

  useEffect(() => {
    if (!actionData?.searchParams || actionData?.errors) {
      setIsSearching(false);
      return;
    }

    const { description, planner, executor, headlessMode, maxListings } = actionData.searchParams;

    const connectToStream = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/search/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            description,
            planner,
            executor,
            headless_mode: headlessMode,
            max_listings: maxListings
          }),
        });

        if (!response.ok) {
          setStreamingError(`Server error: ${response.status} ${response.statusText}`);
          setIsSearching(false);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          setStreamingError("Failed to get stream reader");
          setIsSearching(false);
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            setIsSearching(false);
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const messages = buffer.split("\n\n");
          buffer = messages.pop() || "";

          for (const message of messages) {
            if (!message.startsWith("data: ")) continue;
            try {
              const data = JSON.parse(message.substring(6));
              switch (data.type) {
                case "status":
                  setStreamStatus(prev => [...prev, data.message]);
                  break;
                case "search_results":
                  if (data.urls && Array.isArray(data.urls)) {
                    setListingUrls(data.urls);
                  }
                  break;
                case "listings":
                  setGeocodedListings(data.data);
                  break;
                case "error":
                  setStreamingError(data.message);
                  setIsSearching(false);
                  break;
                case "complete":
                  setIsSearching(false);
                  break;
              }
            } catch (error) {
              console.error("Error parsing event data:", error);
            }
          }
        }
      } catch (error) {
        setStreamingError(`Stream error: ${error instanceof Error ? error.message : String(error)}`);
        setIsSearching(false);
      }
    };

    connectToStream();
  }, [actionData?.searchParams]);

  useEffect(() => {
    if (typeof window !== "undefined" && !mapLoaded) {
      const loadMapbox = async () => {
        try {
          window.mapboxgl = await import("mapbox-gl");
          if (window.mapboxgl && window.ENV?.MAPBOX_ACCESS_TOKEN) {
            window.mapboxgl.accessToken = window.ENV.MAPBOX_ACCESS_TOKEN;
          }
          setMapLoaded(true);
        } catch (error) {
          console.error("Error loading Mapbox:", error);
        }
      };

      loadMapbox();
    }
  }, [mapLoaded]);

  useEffect(() => {
    if (!mapLoaded || !mapContainer.current) return;

    if (map.current) {
      map.current.remove();
      map.current = null;
    }

    const mapboxgl = window.mapboxgl;

    if (!mapboxgl.accessToken) {
      console.error("Mapbox access token is missing. Please set the MAPBOX_ACCESS_TOKEN environment variable.");
      return;
    }

    const sfCoordinates = [-122.4194, 37.7749];
    const bounds = new mapboxgl.LngLatBounds();

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: geocodedListings.length > 0 ? geocodedListings[0].coordinates : sfCoordinates,
      zoom: geocodedListings.length > 0 ? 12 : 12,
      accessToken: window.ENV.MAPBOX_ACCESS_TOKEN,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), "top-right");

    class ResetViewControl {
      _map: any;
      _container: HTMLDivElement = document.createElement('div');
      _bounds: any;

      onAdd(map: any) {
        this._map = map;
        this._bounds = bounds;

        this._container = document.createElement('div');
        this._container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';

        const button = document.createElement('button');
        button.className = 'reset-view-button';
        button.type = 'button';
        button.setAttribute('aria-label', 'Reset map view');
        button.title = 'Reset map view';

        button.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: block; margin: auto;">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          </svg>
        `;

        button.addEventListener('click', () => {
          if (!this._bounds.isEmpty()) {
            this._map.fitBounds(this._bounds, {
              padding: 50,
              maxZoom: 15,
              duration: 1000
            });
          }
        });

        this._container.appendChild(button);
        return this._container;
      }

      onRemove() {
        this._container.parentNode?.removeChild(this._container);
        this._map = undefined;
      }
    }

    map.current.addControl(new ResetViewControl(), 'top-right');

    if (geocodedListings.length > 0) {
      geocodedListings.forEach((listing) => {
        if (listing.coordinates[0] === 0 && listing.coordinates[1] === 0) {
          return;
        }

        if (!listing.coordinates || listing.coordinates.length !== 2) {
          return;
        }

        const el = document.createElement("div");
        el.className = "price-marker";

        const price = typeof listing.listing_details.price === 'number'
          ? listing.listing_details.price
          : parseInt(String(listing.listing_details.price).replace(/\D/g, ''));

        el.innerHTML = `<div class="price-marker-inner">$${price.toLocaleString()}</div>`;

        const popup = new mapboxgl.Popup({
          offset: 15,
          closeButton: true,
          closeOnClick: true,
          className: 'listing-popup',
          maxWidth: '300px'
        })
          .setHTML(`
          <div class="listing-popup-content">
            <div class="listing-popup-image">
              ${listing.listing_details.images && listing.listing_details.images.length > 0
              ? `<img src="${listing.listing_details.images[0]}" alt="${listing.listing_details.title}" />`
              : '<div class="no-image">No image</div>'
            }
            </div>
            <div class="listing-popup-details">
              <a href="${listing.listing_details.url}" target="_blank"><h3>${listing.listing_details.title}</h3></a>
              <p class="listing-price">$${price.toLocaleString()}/mo</p>
              <p class="listing-specs">
                ${listing.listing_details.bedrooms} BR
                ${listing.listing_details.bathrooms ? ` · ${listing.listing_details.bathrooms} BA` : ''}
              </p>
            </div>
          </div>
        `);

        new mapboxgl.Marker({
          element: el,
          anchor: 'center',
          rotationAlignment: 'map',
          pitchAlignment: 'map'
        })
          .setLngLat(listing.coordinates)
          .setPopup(popup)
          .addTo(map.current);

        el.addEventListener("click", () => {
          setSelectedListing(listing);
        });

        bounds.extend(listing.coordinates);
      });

      if (!bounds.isEmpty()) {
        map.current.fitBounds(bounds, {
          padding: 50,
          maxZoom: 15,
        });
      }
    }
  }, [mapLoaded, geocodedListings]);

  const toggleListingExpanded = (listingId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setExpandedListings(prev => ({
      ...prev,
      [listingId]: !prev[listingId]
    }));
  };

  const toggleUrlsPanel = (event: React.MouseEvent) => {
    event.stopPropagation();
    setExpandedUrlsPanel(prev => !prev);
  };

  return (
    <div className="container mx-auto px-2">
      <div className="bg-white py-6">
        <h1 className="text-left flex items-center justify-start px-4">
          <span className="text-3xl font-bold">🏠 craigslist agent 🤖</span>
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Form Column */}
        <div className="md:col-span-1">
          <div className="p-4 bg-white border border-gray-200 rounded-lg shadow">
            <form id="search-form" onSubmit={handleSubmit} className="space-y-4">
              <div>
                <textarea
                  placeholder="describe your ideal apartment (location, bedrooms, bathrooms, price range)"
                  name="description"
                  id="description"
                  className="w-full mt-1 form-control py-2 px-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-black focus:border-black bg-white"
                  style={{ height: "120px", textAlign: "left", verticalAlign: "top" }}
                  required
                />
              </div>

              <div>
                <label htmlFor="planner" className="block text-sm font-medium text-gray-700">
                  planner
                </label>
                <select
                  id="planner"
                  name="planner"
                  className="mt-1 block w-full text-xs py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-black focus:border-black"
                  value={selectedPlanner}
                  onChange={(e) => setSelectedPlanner(e.target.value)}
                >
                  <option value="gpt-4o-mini">gpt-4o-mini</option>
                  <option value="gpt-4o">gpt-4o</option>
                  <option value="claude-3-5-sonnet-latest">claude-3.5-sonnet</option>
                </select>
              </div>

              <div>
                <label htmlFor="executor" className="block text-sm font-medium text-gray-700">
                  executor
                </label>
                <select
                  id="executor"
                  name="executor"
                  className="mt-1 block w-full text-xs py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-black focus:border-black"
                  value={selectedExecutor}
                  onChange={(e) => setSelectedExecutor(e.target.value)}
                >
                  <option value="gpt-4o-mini">gpt-4o-mini</option>
                  <option value="gpt-4o">gpt-4o</option>
                  <option value="claude-3-5-sonnet-latest">claude-3.5-sonnet</option>
                </select>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  name="headlessMode"
                  id="headlessMode"
                  value="true"
                  checked={headlessMode}
                  onChange={(e) => setHeadlessMode(e.target.checked)}
                  className="h-4 w-4 text-black focus:ring-black border-gray-300 rounded"
                />
                <label htmlFor="headlessMode" className="ml-2 block text-sm text-gray-700">
                  headless
                </label>
              </div>

              <div>
                <label htmlFor="maxListings" className="block text-sm font-medium text-gray-700">
                  max listings
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  name="maxListings"
                  id="maxListings"
                  defaultValue={actionData?.fields?.maxListings || "10"}
                  className={`mt-1 block w-full text-xs py-2 px-3 border ${actionData?.errors?.maxListings ? 'border-red-500' : 'border-gray-300'} bg-white rounded-md shadow-sm focus:outline-none focus:ring-black focus:border-black`}
                  style={{
                    appearance: 'textfield',
                    WebkitAppearance: 'none',
                    MozAppearance: 'textfield'
                  }}
                  aria-invalid={Boolean(actionData?.errors?.maxListings)}
                  aria-errormessage={actionData?.errors?.maxListings ? "max-listings-error" : undefined}
                />
                {actionData?.errors?.maxListings && (
                  <div id="max-listings-error" className="text-red-500 text-xs mt-1">
                    {actionData.errors.maxListings}
                  </div>
                )}
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isSearching}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-black hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black disabled:bg-gray-400"
                >
                  {isSearching ? "searching..." : "search craigslist"}
                </button>
              </div>
            </form>
          </div>

          {/* Streaming Status Panel */}
          {(streamStatus.length > 0 || isSearching) && (
            <div className="p-4 bg-white border border-gray-200 rounded-lg shadow mt-4">
              <div className="mb-3 max-h-60 overflow-y-auto">
                {streamStatus.map((message, index) => (
                  <div
                    key={index}
                    className={`py-1 text-sm border-b border-gray-100 last:border-0 ${isSearching &&
                      index === streamStatus.length - 1 ?
                      'animate-pulse flex items-center' : 'flex items-center justify-between'
                      }`}
                  >
                    <div className="flex items-center">
                      {isSearching &&
                        index === streamStatus.length - 1 && (
                          <div className="mr-2 inline-block animate-spin h-3 w-3 border-2 border-black rounded-full border-t-transparent"></div>
                        )}
                      {message}
                    </div>
                    {message.includes("📋 inspecting listings") && (
                      <div className="ml-auto">
                        <button
                          className="p-1 rounded-full hover:bg-gray-100 transition-colors"
                          onClick={toggleUrlsPanel}
                          aria-label={expandedUrlsPanel ? "Collapse URLs" : "Expand URLs"}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className={`h-4 w-4 transition-transform duration-200 ${expandedUrlsPanel ? 'transform rotate-180' : ''} inline-block`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                          {listingUrls.length > 0 && (
                            <span className="ml-1 text-xs text-gray-500">({listingUrls.length})</span>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                ))}

                {expandedUrlsPanel && listingUrls.length > 0 && (
                  <div className="mt-2 px-3 py-3 bg-gray-50 rounded-md border border-gray-200 shadow-sm">
                    <div className="flex justify-between items-center mb-2">
                      <p className="text-xs font-medium text-gray-700">found {listingUrls.length} listings:</p>
                      <button
                        onClick={toggleUrlsPanel}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        hide
                      </button>
                    </div>
                    <div className="max-h-48 overflow-y-auto pr-1">
                      {listingUrls.map((url, urlIndex) => {
                        let displayUrl = url;
                        try {
                          const urlObj = new URL(url);
                          displayUrl = urlObj.hostname + urlObj.pathname;
                          if (displayUrl.length > 50) {
                            displayUrl = displayUrl.substring(0, 47) + '...';
                          }
                        } catch (e) {
                          // Use the original URL if parsing fails
                        }

                        return (
                          <div key={urlIndex} className="py-1.5 border-b border-gray-100 last:border-0 group">
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center text-xs hover:underline text-gray-700 hover:text-blue-600 transition-colors"
                            >
                              <svg className="h-3 w-3 mr-1.5 text-gray-400 group-hover:text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                              <span className="truncate">{displayUrl}</span>
                            </a>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {streamingError && (
                <div className="mt-2 text-sm text-red-600">
                  Error: {streamingError}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Map Column */}
        <div className="md:col-span-2">
          <div
            ref={mapContainer}
            className="h-[600px] rounded-lg shadow-lg border border-gray-200"
          ></div>

          {/* Listings Table/Grid below map - only shown when there are listings */}
          {geocodedListings.length > 0 && (
            <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg shadow">
              <div className="grid grid-cols-1 gap-4">
                {geocodedListings.map((listing, index) => {
                  const listingId = `listing-${index}`;
                  const isExpanded = expandedListings[listingId] || false;
                  const thumbnailImage = listing.listing_details.images && listing.listing_details.images.length > 0
                    ? listing.listing_details.images[0]
                    : 'https://placehold.co/400x300?text=No+Image';

                  return (
                    <div
                      key={index}
                      className={`rounded-md border ${selectedListing === listing ? 'border-gray-400' : 'border-gray-200'} hover:border-gray-300 transition-all duration-200 overflow-hidden`}
                    >
                      <div
                        className="p-4 cursor-pointer grid grid-cols-4 gap-4 items-center"
                        onClick={() => {
                          setSelectedListing(listing === selectedListing ? null : listing);
                          if (map.current && listing.coordinates) {
                            map.current.flyTo({
                              center: listing.coordinates,
                              zoom: 15,
                              duration: 1000
                            });
                          }
                        }}
                      >
                        <div className="col-span-1">
                          <div className="h-24 bg-gray-100 rounded overflow-hidden relative">
                            <img
                              src={thumbnailImage}
                              alt={listing.listing_details.title}
                              className="w-full h-full object-cover"
                            />
                          </div>
                        </div>

                        <div className="col-span-3 flex flex-col justify-between h-full">
                          <div>
                            <a
                              href={listing.listing_details.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-lg hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {listing.listing_details.title}
                            </a>
                            <p className="text-gray-600 text-sm">{listing.listing_details.location}</p>
                          </div>

                          <div className="flex justify-between items-center mt-2">
                            <div>
                              <p className="text-lg font-semibold">{listing.listing_details.price}/mo</p>
                              <div className="flex items-center mt-1">
                                <span className="inline-block bg-gray-100 px-2 py-0.5 rounded mr-2 text-xs">
                                  {listing.listing_details.bedrooms} BR
                                </span>
                                {listing.listing_details.bathrooms && (
                                  <span className="inline-block bg-gray-100 px-2 py-0.5 rounded text-xs">
                                    {listing.listing_details.bathrooms} BA
                                  </span>
                                )}
                              </div>
                            </div>

                            <button
                              className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                              onClick={(e) => toggleListingExpanded(listingId, e)}
                              aria-label={isExpanded ? "Collapse images" : "Expand images"}
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className={`h-5 w-5 transition-transform duration-200 ${isExpanded ? 'transform rotate-180' : ''}`}
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="px-4 pb-4 pt-0 border-t border-gray-100">
                          <p className="text-gray-700 mb-3">{listing.listing_details.description}</p>

                          {listing.listing_details.images && listing.listing_details.images.length > 0 ? (
                            <div className="columns-2 sm:columns-3 gap-3 space-y-3">
                              {listing.listing_details.images.map((image, imgIndex) => (
                                <div
                                  key={imgIndex}
                                  className="relative bg-gray-100 rounded overflow-hidden break-inside-avoid"
                                >
                                  <img
                                    src={image}
                                    alt={`${listing.listing_details.title} - image ${imgIndex + 1}`}
                                    className="w-full object-cover"
                                    loading="lazy"
                                  />
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-4 text-gray-500">no additional images available</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
