from fastapi import FastAPI
from app.routes import webhooks



app = FastAPI(
    title="AI Code Review Bot",
    description="Intelligent GitHub App for automated code reviews and repository audits",
    version="1.0.0",
)

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])