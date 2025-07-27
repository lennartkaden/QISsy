"""
Main file for QISsy FastAPI Application
"""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi_versioning import VersionedFastAPI

__version__ = "v1.0"

from versions.v1.user_routes import router as v1_router


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    base_app = FastAPI(
        title="QISsy",
        description="A simple API to access the QIS server of a University",
    )

    base_app.include_router(v1_router)

    versioned_app = VersionedFastAPI(
        app=base_app,
        enable_latest=True,
        prefix_format="/v{major}.{minor}",
        version_format="{major}.{minor}",
    )

    return versioned_app


app = create_app()


@app.get("/info")
async def info() -> dict[str, str]:
    """Return information about this QISsy instance."""
    return {"name": "QISsy", "version": __version__}


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt() -> PlainTextResponse:
    """Disallow all web crawlers."""
    return PlainTextResponse("User-agent: *\nDisallow: /")
