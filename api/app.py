from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="Generative Ads AI",
    description="API for generating AI-powered ad creatives.",
    version="1.0.0",
)

app.include_router(router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
