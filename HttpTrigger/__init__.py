import traceback

import azure.functions as func

_import_error = None
_asgi_main = None

try:
    from app.main import app as fastapi_app

    _asgi_main = func.AsgiMiddleware(fastapi_app).main
except Exception as exc:
    _import_error = f"{type(exc).__name__}: {exc}"
    _trace = traceback.format_exc()


def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    if _asgi_main is not None:
        return _asgi_main(req, context)

    message = (
        "FastAPI app failed to import during function startup.\n\n"
        f"Error: {_import_error}\n\n"
        f"Traceback:\n{_trace}"
    )
    return func.HttpResponse(message, status_code=500, mimetype="text/plain")
