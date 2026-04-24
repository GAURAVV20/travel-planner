from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from crewai_tools import SerperDevTool
from crewai.tools import BaseTool
import requests
import os
import json
import re
import time
from typing import Optional

load_dotenv()

app = FastAPI(title="Travel Itinerary Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = LLM(
    model="gemini/gemini-3.1-flash-lite-preview",
    api_key=os.environ.get("GOOGLE_API_KEY")
)

search_tool = SerperDevTool(
    api_key=os.environ.get("SERPER_API_KEY"),
    n_results=5
)

RAPIDAPI_KEY  = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "sky-scrapper3.p.rapidapi.com"


def get_airport_skyid(city_name: str) -> Optional[dict]:
    """
    Search for airport SkyId and EntityId by city name.
    Required before searching for flights.
    """
    url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchAirport"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
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


def search_flights(
    origin_city: str,
    destination_city: str,
    depart_date: str,
    return_date: str,
    currency: str = "USD"
) -> dict:
    """
    Search for round-trip flights using Sky Scrapper API.
    Returns real prices from Skyscanner data.
    """

    origin      = get_airport_skyid(origin_city)
    destination = get_airport_skyid(destination_city)

    if not origin or not destination:
        return {"error": "Could not find airports for given cities."}

    print(f"Origin airport: {origin}")
    print(f"Destination airport: {destination}")

    url = f"https://{RAPIDAPI_HOST}/api/v2/flights/searchFlightsComplete"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
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


class FlightSearchTool(BaseTool):
    """
    Custom CrewAI tool that calls Sky Scrapper API
    to get real-time round-trip flight prices.
    """
    name: str        = "Flight Search Tool"
    description: str = (
        "Searches for real round-trip flight prices using Skyscanner data. "
        "Input must be a JSON string with keys: "
        "origin_city, destination_city, depart_date, return_date, currency. "
        'Example: {"origin_city": "Chennai", "destination_city": "Hyderabad", '
        '"depart_date": "2025-06-01", "return_date": "2025-06-05", "currency": "INR"}'
    )

    def _run(self, input_data: str) -> str:
        """Execute real flight search and return price data."""
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


class TripRequest(BaseModel):
    destination:   str
    from_location: str
    budget:        float
    days:          int
    start_date:    str
    end_date:      str
    travel_style:  str = ""
    currency:      str = "USD"


CURRENCY_CONTEXT = {
    "INR": "Indian Rupees. 1 USD ≈ 83 INR. Domestic India flights: INR 3,000-15,000 one way. International: INR 30,000-150,000 round trip. Budget hotels: INR 1,500-5,000/night.",
    "USD": "US Dollars. Domestic flights: $100-$500. International: $300-$1,500. Budget hotels: $50-$150/night.",
    "EUR": "Euros. European flights: €50-€400. International: €250-€1,200. Budget hotels: €40-€120/night.",
}

def build_crew(
    destination:   str,
    from_location: str,
    budget:        float,
    days:          int,
    start_date:    str,
    end_date:      str,
    travel_style:  str,
    currency:      str
):
    """
    Builds a 4-agent CrewAI crew:
    1. Flight Agent   - real prices via Sky Scrapper
    2. Research Agent - hotels & activities via Serper
    3. Budget Agent   - allocates budget with real data
    4. Itinerary Agent - compiles final plan
    """

    currency_note = CURRENCY_CONTEXT.get(currency, "")
    flight_tool   = FlightSearchTool()

    flight_agent = Agent(
        role="Flight Price Agent",
        goal=(
            f"Find the REAL round-trip flight price from {from_location} to "
            f"{destination} for {start_date} to {end_date} in {currency} "
            f"using the Flight Search Tool."
        ),
        backstory=(
            "You are a flight price specialist who uses real-time Skyscanner data. "
            "You always use the Flight Search Tool to get actual prices. "
            "You never guess or estimate flight prices."
        ),
        tools=[flight_tool],
        llm=llm,
        verbose=True,
        max_iter=3
    )

    research_agent = Agent(
        role="Travel Research Agent",
        goal=(
            f"Find real hotel prices and top activities for {destination} "
            f"for {days} days in {currency}."
        ),
        backstory=(
            "You are a travel researcher who searches the web for real hotel "
            "rates and activity costs. " + currency_note
        ),
        tools=[search_tool],
        llm=llm,
        verbose=True,
        max_iter=3
    )

    budget_agent = Agent(
        role="Budget Planner Agent",
        goal=(
            f"Using the REAL flight price and researched hotel/activity costs, "
            f"allocate {currency} {budget} across the full trip. "
            f"All values must sum exactly to {budget}."
        ),
        backstory=(
            "You are a strict budget planner who only uses verified real prices. "
            "You never invent costs. " + currency_note
        ),
        llm=llm,
        verbose=True,
        max_iter=3
    )

    itinerary_agent = Agent(
        role="Itinerary Compiler Agent",
        goal=(
            f"Compile all data into a detailed {days}-day itinerary "
            f"for {destination} with real place names and verified costs."
        ),
        backstory=(
            "You are a travel itinerary specialist who creates practical "
            "day-by-day plans using real locations and verified costs."
        ),
        llm=llm,
        verbose=True,
        max_iter=3
    )

    flight_task = Task(
        description=(
            f"Use the Flight Search Tool to find real round-trip flight prices.\n"
            f"Call the tool with this exact JSON:\n"
            f'{{"origin_city": "{from_location}", "destination_city": "{destination}", '
            f'"depart_date": "{start_date}", "return_date": "{end_date}", "currency": "{currency}"}}\n\n'
            f"Report the lowest, average, and highest prices found along with airline names."
        ),
        expected_output=(
            f"Real round-trip flight prices in {currency} from {from_location} to "
            f"{destination} with lowest, average, highest price and top airlines."
        ),
        agent=flight_agent
    )

    research_task = Task(
        description=(
            f"Search the web for:\n"
            f"1. 'budget hotel {destination} per night {currency} {start_date}'\n"
            f"2. 'top tourist attractions {destination} entry fee {currency}'\n"
            f"3. 'average food cost per day {destination} tourist {currency}'\n"
            f"4. 'local transport cost {destination} per day {currency}'\n\n"
            f"Travel style: {travel_style if travel_style else 'general tourist'}\n"
            f"Only report prices actually found in search results."
        ),
        expected_output=(
            f"Hotel nightly rate, top 5 activities with costs, "
            f"daily food budget, and transport costs — all in {currency}."
        ),
        agent=research_agent
    )

    budget_task = Task(
        description=(
            f"Using the REAL flight price from Task 1 and research from Task 2,\n"
            f"allocate {currency} {budget} for a {days}-day trip.\n\n"
            f"Rules:\n"
            f"- Use the ACTUAL flight price found by the Flight Agent\n"
            f"- Hotel = nightly rate × {days} nights\n"
            f"- Food = daily budget × {days} days\n"
            f"- Activities = sum of planned activities\n"
            f"- Misc = remainder to reach exactly {budget}\n"
            f"- ALL 5 values MUST sum exactly to {budget}\n"
            f"- {currency_note}"
        ),
        expected_output=(
            f"Budget breakdown in {currency}: flights, accommodation, food, "
            f"activities, misc — summing exactly to {budget}."
        ),
        agent=budget_agent,
        context=[flight_task, research_task]
    )

    itinerary_task = Task(
        description=(
            f"Compile all data into a {days}-day itinerary for {destination}.\n"
            f"Use REAL place names and the verified budget breakdown.\n"
            f"Each day must show the actual date starting from {start_date}.\n\n"
            f"Return ONLY a raw valid JSON object — no markdown, no backticks:\n"
            "{\n"
            '  "destination": "string",\n'
            '  "totalBudget": number,\n'
            '  "currency": "string",\n'
            '  "budgetBreakdown": {\n'
            '    "flights": number,\n'
            '    "accommodation": number,\n'
            '    "food": number,\n'
            '    "activities": number,\n'
            '    "misc": number\n'
            '  },\n'
            '  "accommodation": "string (real hotel name and area)",\n'
            '  "days": [\n'
            '    {\n'
            '      "day": number,\n'
            '      "date": "string (e.g. 2025-06-01)",\n'
            '      "title": "string",\n'
            '      "morning": "string",\n'
            '      "afternoon": "string",\n'
            '      "evening": "string",\n'
            '      "estimatedCost": number\n'
            '    }\n'
            '  ],\n'
            '  "tips": ["string", "string", "string"]\n'
            "}"
        ),
        expected_output=(
            "A raw valid JSON object with all fields filled using real data. "
            "No markdown, no backticks, pure JSON only."
        ),
        agent=itinerary_agent,
        context=[flight_task, research_task, budget_task]
    )

    crew = Crew(
        agents=[flight_agent, research_agent, budget_agent, itinerary_agent],
        tasks=[flight_task, research_task, budget_task, itinerary_task],
        process=Process.sequential,
        verbose=True
    )

    return crew


@app.post("/generate-itinerary")
def generate_itinerary(request: TripRequest):
    """
    Main endpoint — validates input, runs CrewAI agents,
    returns structured itinerary JSON with real flight prices.
    """

    if request.days < 1 or request.days > 30:
        raise HTTPException(status_code=400, detail="Trip duration must be between 1 and 30 days.")

    if request.budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0.")

    if request.from_location.strip().lower() == request.destination.strip().lower():
        raise HTTPException(status_code=400, detail="Origin and destination cannot be the same.")

    if request.currency not in ["USD", "INR", "EUR"]:
        raise HTTPException(status_code=400, detail="Currency must be USD, INR, or EUR.")

    min_budgets = {"USD": 200, "INR": 10000, "EUR": 150}
    if request.budget < min_budgets[request.currency]:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum budget for {request.currency} is {min_budgets[request.currency]}."
        )

    try:
        crew = build_crew(
            destination=request.destination,
            from_location=request.from_location,
            budget=request.budget,
            days=request.days,
            start_date=request.start_date,
            end_date=request.end_date,
            travel_style=request.travel_style,
            currency=request.currency
        )

        max_retries = 3
        result = None
        for attempt in range(max_retries):
            try:
                result = crew.kickoff()
                break
            except Exception as e:
                error_str = str(e)
                if any(code in error_str for code in ["429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                    wait_time = 60 if "429" in error_str else 5
                    print(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                raise e

        raw = str(result).strip()
        if "```" in raw:
            raw = re.sub(r"```json|```", "", raw).strip()

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        itinerary = json.loads(raw)

        breakdown = itinerary.get("budgetBreakdown", {})
        total = sum(breakdown.values())
        if abs(total - request.budget) > request.budget * 0.05:
            breakdown["misc"] = round(
                breakdown.get("misc", 0) + (request.budget - total), 2
            )
            itinerary["budgetBreakdown"] = breakdown
            itinerary["totalBudget"] = request.budget

        return {"success": True, "itinerary": itinerary}

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Agent returned malformed response. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
