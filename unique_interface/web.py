"""Full-page chat for local Python and Hugging Face Static Spaces."""
import json
import re
import time
import webbrowser
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock


def _page(**options):
    assets = files("unique_interface")
    config = json.dumps(options).replace("<", "\\u003c")
    return assets.joinpath("chat.html").read_text(encoding="utf-8").replace(
        "__LOGO__", assets.joinpath("logo.b64").read_text().strip()
    ).replace("__CONFIG__", config)


def export_space(path="index.html", *, model="HuggingFaceTB/SmolLM2-135M-Instruct", title="UniqueChat"):
    """Write the browser-inference app for a Hugging Face Static Space."""
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(_page(mode="browser", model=model, title=title))
    return Path(path)


def serve(fn, *, title="UniqueChat", port=0, open_browser=True):
    """Run a loopback-only chat using fn(message, history) until Ctrl+C."""
    page = _page(mode="python", title=title).encode()
    model_lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path != "/" or self.headers.get("Host") != authority:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            if (self.path != "/reply" or self.headers.get("Host") != authority
                    or self.headers.get("Origin") != url or self.headers.get("X-Unique-Chat") != "1"):
                return self.send_error(403)
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 262144:
                    return self.send_error(413)
                data = json.loads(self.rfile.read(size))
                msg, history = data["message"], data["history"]
                if not isinstance(msg, str) or not msg.strip() or not isinstance(history, list):
                    raise ValueError
                if any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                       or not isinstance(m.get("content"), str) for m in history):
                    raise ValueError
            except (KeyError, ValueError, TypeError):
                return self.send_error(400)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def emit(item):
                self.wfile.write((json.dumps(item) + "\n").encode())
                self.wfile.flush()

            try:
                with model_lock:
                    result = fn(msg, history)
                    if isinstance(result, str):
                        for chunk in re.findall(r"\s+|\S+\s*", result):
                            emit({"text": chunk})
                            time.sleep(0.015)
                    elif isinstance(result, Iterator):
                        for chunk in result:
                            if not isinstance(chunk, str):
                                raise TypeError
                            emit({"text": chunk})
                    else:
                        raise TypeError
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                emit({"error": "The reply callback failed."})

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        authority = f"127.0.0.1:{server.server_port}"
        url = f"http://{authority}"
        print(f"Local chat: {url}/", flush=True)
        if open_browser:
            webbrowser.open_new_tab(url + "/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
