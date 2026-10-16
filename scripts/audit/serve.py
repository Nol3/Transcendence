"""Sirve juego/web con las mismas cabeceras que el backend Django (/game-embed/)."""
import functools, http.server, socketserver, sys

ROOT = "/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit/gameweb"
PORT = 8099


class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("0.0.0.0", PORT), functools.partial(H, directory=ROOT)) as httpd:
    print(f"sirviendo {ROOT} en :{PORT}", flush=True)
    httpd.serve_forever()
