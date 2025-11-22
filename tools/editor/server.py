import http.server
import socketserver
import json
import os
import sys

PORT = 8000
# The directory where this script is located
EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))
# The project root (two levels up: tools/editor -> tools -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(EDITOR_DIR))
LAYOUT_FILE = os.path.join(PROJECT_ROOT, "layout.json")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/layout":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if os.path.exists(LAYOUT_FILE):
                with open(LAYOUT_FILE, "r") as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(b"{}")
        else:
            # Explicitly handle MIME types for static files to avoid Windows registry issues
            if self.path.endswith(".js"):
                self.send_response(200)
                self.send_header("Content-type", "application/javascript")
                self.end_headers()
                with open(
                    os.path.join(EDITOR_DIR, self.path.lstrip("/").split("?")[0]), "rb"
                ) as f:
                    self.wfile.write(f.read())
                return
            elif self.path.endswith(".css"):
                self.send_response(200)
                self.send_header("Content-type", "text/css")
                self.end_headers()
                with open(
                    os.path.join(EDITOR_DIR, self.path.lstrip("/").split("?")[0]), "rb"
                ) as f:
                    self.wfile.write(f.read())
                return
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/save":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data)
                # Validate or process if needed
                with open(LAYOUT_FILE, "w") as f:
                    json.dump(data, f, indent=2)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Layout saved"}')
                print(f"Layout saved to {LAYOUT_FILE}")
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "error", "message": str(e)}).encode()
                )
        else:
            self.send_error(404)


if __name__ == "__main__":
    # Change to the editor directory so we can serve index.html easily
    os.chdir(EDITOR_DIR)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving Editor at http://localhost:{PORT}")
        print(f"Editing layout file: {LAYOUT_FILE}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
