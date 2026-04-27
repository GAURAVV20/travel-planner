from crewai import Crew, Process
from agents import create_agents
from tasks import create_tasks


def build_crew(destination, from_location, budget, days, start_date, end_date, travel_style, currency):
    """
    Assembles the full CrewAI crew with 4 agents and 4 tasks.

    Process: Sequential
        Flight Agent → Research Agent → Budget Agent → Itinerary Agent
    """

    # Create agents with trip context
    agents = create_agents(
        destination=destination,
        from_location=from_location,
        budget=budget,
        days=days,
        start_date=start_date,
        end_date=end_date,
        currency=currency
    )

    # Create tasks and assign agents
    tasks = create_tasks(
        agents=agents,
        destination=destination,
        from_location=from_location,
        budget=budget,
        days=days,
        start_date=start_date,
        end_date=end_date,
        travel_style=travel_style,
        currency=currency
    )

    flight_agent, research_agent, budget_agent, itinerary_agent = agents
    flight_task, research_task, budget_task, itinerary_task     = tasks

    # Build and return the crew
    crew = Crew(
        agents=[flight_agent, research_agent, budget_agent, itinerary_agent],
        tasks=[flight_task, research_task, budget_task, itinerary_task],
        process=Process.sequential,
        verbose=True
    )

    return crew
