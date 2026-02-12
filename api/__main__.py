"""Entry point for running the API as a module."""

import uvicorn
from .config import config

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=config.host,
        port=config.port,
        reload=True
    )