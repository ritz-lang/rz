#!/usr/bin/env python3
"""
Python aiohttp server for benchmarking comparison.

Run: python3 server_aiohttp.py
Test: curl http://localhost:8081/health
"""

from aiohttp import web


async def health_handler(request):
    return web.Response(text="OK", content_type="text/plain")


async def root_handler(request):
    return web.Response(text="OK", content_type="text/plain")


def main():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", root_handler)
    print("Python aiohttp server listening on port 8081")
    web.run_app(app, host="0.0.0.0", port=8081, print=None)


if __name__ == "__main__":
    main()
