"""
Main file for QISsy FastAPI Application
"""
from fastapi import FastAPI
from fastapi_versioning import VersionedFastAPI

from versions.v1.user_routes import router as v1_router

app = FastAPI(title="QISsy", description="A simple API to access the QIS server of the Leibniz University Hannover")

app.include_router(v1_router)

app = VersionedFastAPI(app=app, enable_latest=True, prefix_format="/v{major}.{minor}",
                       version_format="{major}.{minor}")
