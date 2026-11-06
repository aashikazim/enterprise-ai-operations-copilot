"""Bounded HTTP input and safe response defaults without changing JWT auth."""
import logging

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse


logger = logging.getLogger("copilot.http")


class SecurityMiddleware:
    MAX_BODY_BYTES = 1024 * 1024

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False
        async def safe_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Cache-Control"] = "no-store"
                # Swagger/Redoc retain their existing script/CSS behavior.
                if not scope.get("path", "").startswith(("/docs", "/redoc")):
                    headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
            await send(message)

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, safe_send)

        try:
            if scope.get("method") in {"POST", "PUT", "PATCH"}:
                lengths = [value for key, value in scope.get("headers", []) if key == b"content-length"]
                if lengths:
                    try:
                        length = int(lengths[0])
                        if length < 0: raise ValueError()
                    except ValueError:
                        return await reject(400, "Invalid request length")
                    if length > self.MAX_BODY_BYTES:
                        return await reject(413, "Request body exceeds limit")
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > self.MAX_BODY_BYTES:
                        return await reject(413, "Request body exceeds limit")
                    if not message.get("more_body", False):
                        break
                delivered = False
                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()
                await self.app(scope, replay, safe_send)
            else:
                await self.app(scope, receive, safe_send)
        except Exception:
            logger.error("HTTP request failed")
            if not started:
                await reject(500, "Internal service error")
