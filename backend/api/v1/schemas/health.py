from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    lm_studio: str