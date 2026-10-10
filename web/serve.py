"""Serve only captured bytes from a complete artifact, at the project base path."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(WEB.parent / "src"))
from techkb.publication import ExportError
from kaname_web.artifact import load_artifact


def server(artifact, port=8765):
    _, files = load_artifact(artifact)
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.respond(False)
        def do_GET(self):
            self.respond(True)
        def respond(self, body):
            path = unquote(urlsplit(self.path).path)
            if path in {"/", "/kaname"}:
                self.send_response(302); self.send_header("Location", "/kaname/"); self.end_headers(); return
            if not path.startswith("/kaname/") or ".." in path.split("/") or "\\" in path:
                self.send_error(404); return
            name = path.removeprefix("/kaname/") or "index.html"
            if name.endswith("/"): name += "index.html"
            if name not in files and name + ".html" in files: name += ".html"
            if name not in files:
                self.send_error(404); return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(files[name])))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if body: self.wfile.write(files[name])
        def log_message(self, *args):
            pass
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        output = args.artifact or json.loads((WEB / ".cache/last-build.json").read_bytes())["output"]
        httpd = server(output, args.port)
        print(f"Preview: http://127.0.0.1:{httpd.server_port}/kaname/", flush=True)
        httpd.serve_forever()
    except (ExportError, OSError, ValueError, KeyError):
        print("preview_unavailable", file=sys.stderr); sys.exit(1)
