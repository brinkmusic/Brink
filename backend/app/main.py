# WHAT THIS FILE IS
# The starting point of the backend. It creates the app and plugs in the routes.
# WHY it's tiny: the actual routes live in separate files under routers/, and this
# file just wires them together. When you run the server, it loads "app" from here.

from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Brink API")
app.include_router(health.router)  # add the /api/health route; more routers get added here later
