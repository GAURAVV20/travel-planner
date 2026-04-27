import json
import requests
from typing import Optional
from crewai.tools import BaseTool
from crewai_tools import SerperDevTool

from config import RAPIDAPI_KEY, RAPIDAPI_HOST, SERPER_API_KEY


# Serper Search Tool
search_tool = SerperDevTool(
    api_key=SERPER_API_KEY,
    n_results=5
)

# Sky Scrapper Helpers

def get_airport_skyid(city_name: str) -> Optional[dict]:
    """Search for airport SkyId and EntityId by city name."""
    url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchAirport"
    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {"query": city_name, "locale": "en-US"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if data.get("status") and data.get("data"):
            first = data["data"][0]
            return {
                "skyId":    first.get("skyId"),
                "entityId": first.get("entityId"),
                "name":     first.get("presentation", {}).get("title", city_name)
            }
    except Exception as e:
        print(f"Airport search error: {e}")
    return None

def search_flights(origin_city, destination_city, depart_date, return_date, currency="USD") -> dict:
    """Search round-trip flights using Sky Scrapper API."""

    origin      = get_airport_skyid(origin_city)
    destination = get_airport_skyid(destination_city)

    if not origin or not destination:
        return {"error": "Could not find airports for given cities."}

    print(f"Origin airport: {origin}")
    print(f"Destination airport: {destination}")

    url = f"https://{RAPIDAPI_HOST}/api/v2/flights/searchFlightsComplete"
    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "originSkyId":         origin["skyId"],
        "destinationSkyId":    destination["skyId"],
        "originEntityId":      origin["entityId"],
        "destinationEntityId": destination["entityId"],
        "date":                depart_date,
        "returnDate":          return_date,
        "cabinClass":          "economy",
        "adults":              "1",
        "currency":            currency,
        "locale":              "en-US",
        "market":              "en-US",
        "countryCode":         "US"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()

        if data.get("status") and data.get("data"):
            itineraries = data["data"].get("itineraries", [])

            if itineraries:
                prices  = []
                results = []

                for item in itineraries[:5]:
                    price = item.get("price", {})
                    raw   = price.get("raw", 0)
                    fmt   = price.get("formatted", "N/A")

                    if raw > 0:
                        prices.append(raw)
                        legs     = item.get("legs", [])
                        airline  = ""
                        duration = ""
                        if legs:
                            carriers = legs[0].get("carriers", {}).get("marketing", [])
                            if carriers:
                                airline = carriers[0].get("name", "")
                            mins     = legs[0].get("durationInMinutes", 0)
                            duration = f"{mins // 60}h {mins % 60}m"

                        results.append({
                            "price":     raw,
                            "formatted": fmt,
                            "airline":   airline,
                            "duration":  duration
                        })

                if prices:
                    return {
                        "origin":        origin["name"],
                        "destination":   destination["name"],
                        "depart_date":   depart_date,
                        "return_date":   return_date,
                        "currency":      currency,
                        "lowest_price":  min(prices),
                        "average_price": round(sum(prices) / len(prices), 2),
                        "highest_price": max(prices),
                        "top_flights":   results,
                        "source":        "Skyscanner (real-time)"
                    }

        return {"error": "No flights found.", "raw": str(data)[:300]}

    except Exception as e:
        return {"error": f"Flight search failed: {str(e)}"}


# Custom CrewAI Flight Tool
class FlightSearchTool(BaseTool):
    """Custom CrewAI tool that calls Sky Scrapper API for real flight prices."""

    name: str        = "Flight Search Tool"
    description: str = (
        "Searches for real round-trip flight prices using Skyscanner data. "
        "Input must be a JSON string with keys: "
        "origin_city, destination_city, depart_date, return_date, currency. "
        'Example: {"origin_city": "Chennai", "destination_city": "Hyderabad", '
        '"depart_date": "2025-06-01", "return_date": "2025-06-05", "currency": "INR"}'
    )

    def _run(self, input_data: str) -> str:
        try:
            params = input_data if isinstance(input_data, dict) else json.loads(input_data)
            result = search_flights(
                origin_city=params.get("origin_city", ""),
                destination_city=params.get("destination_city", ""),
                depart_date=params.get("depart_date", ""),
                return_date=params.get("return_date", ""),
                currency=params.get("currency", "USD")
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
