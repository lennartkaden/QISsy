"""
Main file for QISsy FastAPI Application
"""

from fastapi import FastAPI

from versions.v1.user_routes import router as v1_router

app = FastAPI()

# set the name of the app
app.title = "QISsy"

app.include_router(v1_router, prefix="/v1")
