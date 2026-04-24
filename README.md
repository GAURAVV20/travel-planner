# Travel Itinerary Planner

A Gen AI project using an Agentic AI approach.
- **Frontend**: React (Vite)
- **Backend**: Python FastAPI
- **AI**: Anthropic Claude (multi-agent prompting)

---

## Project Structure

```
travel-planner/
├── backend/
│   ├── main.py            # FastAPI app + AI Agent logic
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── main.jsx
    │   └── App.jsx        # React UI
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## Setup & Run

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_api_key_here   # Mac/Linux
set ANTHROPIC_API_KEY=your_api_key_here      # Windows

# Start the server
uvicorn main:app --reload
# Runs on http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### 3. Open your browser
Go to `http://localhost:5173`

---

## How It Works (Agentic AI Flow)

```
User Input (destination, budget, days)
        ↓
   React Frontend
        ↓  POST /generate-itinerary
   FastAPI Backend
        ↓
   Claude AI Agent
   ┌─────────────────────────────┐
   │  Flight Agent               │
   │  Hotel Agent                │
   │  Activity Agent             │
   │  Budget Allocator           │
   │  Itinerary Compiler         │
   └─────────────────────────────┘
        ↓
   Structured JSON Itinerary
        ↓
   React renders day-by-day plan
```

The system prompt instructs Claude to act as multiple sub-agents internally,
reason through each role, and return a structured JSON itinerary.
