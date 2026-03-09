from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

from app.middleware.request_logger import RequestLoggingMiddleware
from app.core.exceptions import global_exception_handler
from app.routers import health, repos, chat, api_keys, credentials, workflows, agent

load_dotenv()

# Logger setup
logger = logging.getLogger("explaingithub")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Explaingithub")

# Middleware
app.add_middleware(RequestLoggingMiddleware)

# Exception Handler
app.add_exception_handler(Exception, global_exception_handler)

# Routers
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(api_keys.router)
app.include_router(credentials.router)
app.include_router(workflows.router)
app.include_router(health.router)
app.include_router(agent.router)
