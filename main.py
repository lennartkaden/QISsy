"""
Main file for QISsy FastAPI Application
"""
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI

__version__ = "0.1.0-devpreview.1"

from versions.v1.user_routes import router as v1_router

base_app = FastAPI(title="QISsy", description="A simple API to access the QIS server of a University")

base_app.include_router(v1_router)

@base_app.get("/info")
async def info():
    """Return information about this QISsy instance."""
    return {"name": "QISsy", "version": __version__}

app = VersionedFastAPI(app=base_app, enable_latest=True, prefix_format="/v{major}.{minor}",
                       version_format="{major}.{minor}")
