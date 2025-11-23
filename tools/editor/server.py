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
        elif self.path == "/api/layouts":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
            if not os.path.exists(layouts_dir):
                os.makedirs(layouts_dir)
            files = [f for f in os.listdir(layouts_dir) if f.endswith(".json")]
            self.wfile.write(json.dumps(files).encode())
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
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        if self.path == "/api/save":
            try:
                req = json.loads(post_data)
                # Handle both legacy (direct data) and new (wrapped data) formats
                if "data" in req:
                    data = req["data"]
                    filename = req.get("filename")
                else:
                    data = req
                    filename = None

                # Always save to active layout.json
                with open(LAYOUT_FILE, "w") as f:
                    json.dump(data, f, indent=2)

                # If filename provided, also save to layouts directory
                if filename:
                    if not filename.endswith(".json"):
                        filename += ".json"

                    layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
                    if not os.path.exists(layouts_dir):
                        os.makedirs(layouts_dir)

                    filepath = os.path.join(layouts_dir, filename)
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=2)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Layout saved"}')
            except Exception as e:
                self._send_error(str(e))

        elif self.path == "/api/save_as":
            try:
                req = json.loads(post_data)
                filename = req.get("filename")
                data = req.get("data")

                if not filename or not data:
                    raise ValueError("Missing filename or data")

                if not filename.endswith(".json"):
                    filename += ".json"

                layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
                if not os.path.exists(layouts_dir):
                    os.makedirs(layouts_dir)

                filepath = os.path.join(layouts_dir, filename)
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)

                # Also update the active layout file
                with open(LAYOUT_FILE, "w") as f:
                    json.dump(data, f, indent=2)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b'{"status": "success", "message": "Layout saved as new file"}'
                )
            except Exception as e:
                self._send_error(str(e))

        elif self.path == "/api/load":
            try:
                req = json.loads(post_data)
                filename = req.get("filename")

                if not filename:
                    raise ValueError("Missing filename")

                layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
                filepath = os.path.join(layouts_dir, filename)

                if not os.path.exists(filepath):
                    raise FileNotFoundError("Layout file not found")

                with open(filepath, "r") as f:
                    data = json.load(f)

                # Update active layout
                with open(LAYOUT_FILE, "w") as f:
                    json.dump(data, f, indent=2)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self._send_error(str(e))

        elif self.path == "/api/rename":
            try:
                req = json.loads(post_data)
                old_name = req.get("old_filename")
                new_name = req.get("new_filename")

                if not old_name or not new_name:
                    raise ValueError("Missing filenames")

                if not new_name.endswith(".json"):
                    new_name += ".json"

                layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
                old_path = os.path.join(layouts_dir, old_name)
                new_path = os.path.join(layouts_dir, new_name)

                if not os.path.exists(old_path):
                    raise FileNotFoundError("Original file not found")

                os.rename(old_path, new_path)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "File renamed"}')
            except Exception as e:
                self._send_error(str(e))
        elif self.path == "/api/delete_layout":
            try:
                req = json.loads(post_data)
                filename = req.get("filename")

                if not filename:
                    raise ValueError("Missing filename")

                layouts_dir = os.path.join(PROJECT_ROOT, "layouts")
                filepath = os.path.join(layouts_dir, filename)

                if not os.path.exists(filepath):
                    raise FileNotFoundError("Layout file not found")

                os.remove(filepath)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Layout deleted"}')
            except Exception as e:
                self._send_error(str(e))
        else:
            self.send_error(404)

    def _send_error(self, message):
        self.send_response(500)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "error", "message": message}).encode())


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
