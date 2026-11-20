from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request

from src.wallet.routes import routes as wallet_routes

async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})

routes = [
    Route("/health", health_check, methods=["GET"]),
    *wallet_routes
]

app = Starlette(routes=routes)