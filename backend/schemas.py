from pydantic import BaseModel


class TripRequest(BaseModel):
    destination:   str
    from_location: str
    budget:        float
    days:          int
    start_date:    str
    end_date:      str
    travel_style:  str = ""
    currency:      str = "USD"
