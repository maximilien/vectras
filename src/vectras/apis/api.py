import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras API", description="Simple health API", version="0.1.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_API_HOST", "localhost")
    port = int(os.getenv("VECTRAS_API_PORT", "8121"))
    uvicorn.run(app, host=host, port=port)
