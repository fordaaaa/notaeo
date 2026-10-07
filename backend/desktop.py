"""Local loopback server used by the native desktop applications.

Binds 127.0.0.1 only on an ephemeral port. The shell passes a per-launch
RESEARCH_DESKTOP_TOKEN as a native request header; account login (Bearer)
is still mandatory on data routes. API-only: no website is served.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from api.main import create_app

DESKTOP_HOST = "127.0.0.1"


def create_desktop_app() -> FastAPI:
    """API-only sidecar; requires launch token plus absolute external data dir."""
    if not os.environ.get("RESEARCH_DESKTOP_TOKEN"):
        raise RuntimeError("desktop sidecar requires RESEARCH_DESKTOP_TOKEN")
    configured = os.environ.get("RESEARCH_DATA_DIR")
    if not configured or not Path(configured).is_absolute():
        raise RuntimeError("native sidecar requires an absolute RESEARCH_DATA_DIR")
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        roots = [executable.parent]
        for parent in executable.parents:
            if parent.suffix == ".app":
                roots.append(parent)
            if parent.name == "Resources":
                roots.append(parent.parent)
        if any(Path(configured).resolve().is_relative_to(root) for root in roots):
            raise RuntimeError("RESEARCH_DATA_DIR must be outside the desktop bundle")
    return create_app()


def serve() -> None:
    """Bind an ephemeral loopback port and announce it before serving requests."""
    app = create_desktop_app()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((DESKTOP_HOST, 0))
    listener.listen()
    port = listener.getsockname()[1]
    print(f"RESEARCH_READY http://{DESKTOP_HOST}:{port}", flush=True)
    # proxy_headers=False is load-bearing: uvicorn defaults it to True, which
    # installs ProxyHeadersMiddleware and rewrites scope["client"] from
    # X-Forwarded-For for trusted (loopback) peers — letting any local process
    # mint fresh auth rate-limit buckets with a spoofed header. The sidecar is
    # loopback-only with no reverse proxy, so the header must never be
    # honored; api/auth.py keys buckets on the TCP peer IP. Pinned explicitly
    # (not relying on the installed default) for forward-compat.
    config = uvicorn.Config(
        app,
        host=DESKTOP_HOST,
        port=port,
        log_level="warning",
        proxy_headers=False,
    )
    uvicorn.Server(config).run(sockets=[listener])


if __name__ == "__main__":
    serve()
