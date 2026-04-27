from crewai import Task
from config import CURRENCY_CONTEXT


def create_tasks(agents, destination, from_location, budget, days, start_date, end_date, travel_style, currency):
    """Create and return all 4 tasks with trip-specific context."""

    flight_agent, research_agent, budget_agent, itinerary_agent = agents
    currency_note = CURRENCY_CONTEXT.get(currency, "")

    # Task 1: Flight Search
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

    # Task 2: Research Task
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

    # Task 3: Budget Task
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

    # Task 4: Itinerary Task
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

    return flight_task, research_task, budget_task, itinerary_task
