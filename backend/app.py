"""FastAPI composition root for the Zeteo Diagnostic backend."""

from fastapi import FastAPI

# Import every table before the application can initialize a database.
import backend.models  # noqa: F401
from backend.api.routes import router

app = FastAPI(title="Zeteo API")
app.include_router(router)
