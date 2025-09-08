import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api-logger")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # --- Log Request ---
        try:
            body = await request.body()
            body_text = body.decode("utf-8") if body else None
        except Exception:
            body_text = None

        logger.info(
            f"\n\n"
            f"REQUEST: {request.method} {request.url} "
            f"Headers={dict(request.headers)} "
            f"Body={body_text}"
            f"\n"
        )

        # --- Call Next Middleware / Endpoint ---
        response = await call_next(request)

        # --- Log Response ---
        process_time = (time.time() - start_time) * 1000
        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # bikin async generator baru biar sesuai dengan ekspektasi ASGI
            async def new_body_iterator():
                yield response_body

            response.body_iterator = new_body_iterator()
            body_text = response_body.decode("utf-8")
        except Exception:
            body_text = "<streaming or non-text response>"

        logger.info(
            f"\n\n"
            f"RESPONSE: status={response.status_code} "
            f"Time={process_time:.2f}ms "
            f"Body={body_text}"
            f"\n"
        )

        return response
