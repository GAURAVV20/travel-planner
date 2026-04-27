"""
config.py
---------
Central configuration — loads environment variables,
sets up the LLM, and defines currency context constants.
"""

import os
from dotenv import load_dotenv
from crewai.llm import LLM
load_dotenv()

# API Keys 
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
RAPIDAPI_KEY   = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST  = "sky-scrapper3.p.rapidapi.com"

# LLM
llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
)


# Currency context strings used in agent prompts
CURRENCY_CONTEXT = {
    "INR": "Indian Rupees. 1 USD ≈ 83 INR. Domestic India flights: INR 3,000–15,000 one way. International: INR 30,000–150,000 round trip. Budget hotels: INR 1,500–5,000/night.",
    "USD": "US Dollars. Domestic flights: $100–$500. International: $300–$1,500. Budget hotels: $50–$150/night.",
    "EUR": "Euros. European flights: €50–€400. International: €250–€1,200. Budget hotels: €40–€120/night.",
}

# Minimum budgets per currency
MIN_BUDGETS = {"USD": 200, "INR": 10000, "EUR": 150}
