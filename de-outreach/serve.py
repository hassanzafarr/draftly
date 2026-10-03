#!/usr/bin/env python3
"""Run the tool locally: python3 serve.py  ->  http://localhost:8765

Serves index.html and routes /api/de to the same handler Vercel runs.
"""

import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))
import de  # noqa: E402

PUBLIC = {"/", "/index.html"}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/api/de":
            return de.handler.do_GET(self)
        if self.path.split("?")[0] not in PUBLIC:  # don't serve the source tree, your CSV exports or .env
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/de":
            return de.handler.do_POST(self)
        return self.send_error(404)

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = int(os.environ.get("PORT", 8765))
    print(f"DE Outreach running at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
