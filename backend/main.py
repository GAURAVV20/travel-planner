"""
main.py
-------
FastAPI application entry point.
Handles CORS, input validation, crew execution, and response formatting.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import re
import time

from schemas import TripRequest
from crew import build_crew
from config import MIN_BUDGETS


# App Setup
app = FastAPI(title="Travel Itinerary Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints

@app.post("/generate-itinerary")
def generate_itinerary(request: TripRequest):
    """
    Main endpoint — validates input, runs CrewAI agents,
    returns structured itinerary JSON with real flight prices.
    """

    # Input Validation
    if request.days < 1 or request.days > 30:
        raise HTTPException(status_code=400, detail="Trip duration must be between 1 and 30 days.")

    if request.budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be greater than 0.")

    if request.from_location.strip().lower() == request.destination.strip().lower():
        raise HTTPException(status_code=400, detail="Origin and destination cannot be the same.")

    if request.currency not in ["USD", "INR", "EUR"]:
        raise HTTPException(status_code=400, detail="Currency must be USD, INR, or EUR.")

    if request.budget < MIN_BUDGETS[request.currency]:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum budget for {request.currency} is {MIN_BUDGETS[request.currency]}."
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

        # Retry logic for rate limit errors
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

        # Parse JSON response from agent output
        raw = str(result).strip()
        if "```" in raw:
            raw = re.sub(r"```json|```", "", raw).strip()

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        itinerary = json.loads(raw)

        # Validate & fix budget totals if off by more than 5%
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
