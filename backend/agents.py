from crewai import Agent
from config import llm, CURRENCY_CONTEXT
from tools import FlightSearchTool, search_tool


def create_agents(destination, from_location, budget, days, start_date, end_date, currency):
    """Create and return all 4 agents with trip-specific context."""

    currency_note = CURRENCY_CONTEXT.get(currency, "")
    flight_tool   = FlightSearchTool()

    # Agent 1: Flight Agent
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

    # Agent 2: Research Agent
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

    # Agent 3: Budget Agent
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

    # Agent 4: Itinerary Agent
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

    return flight_agent, research_agent, budget_agent, itinerary_agent
