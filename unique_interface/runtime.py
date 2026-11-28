"""HTTP transport shared by function demos and full-page chat."""
import atexit
import json
import os
import threading
import time
import webbrowser
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import urlsplit

from . import sharing
from .web import _page


class App:
    def __init__(self, server):
        self.server = server
        self.local_url = f"http://127.0.0.1:{server.server_port}"
        self.share_url = None
        self._relay = None
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            sharing.stop(self._relay)
            self.server.shutdown()
            self.server.server_close()
            atexit.unregister(self.close)


def launch(*, form=None, chat=None, title="UniqueChat", share=False, port=0,
           open_browser=True, block=None, space=False, concurrency_limit=1, max_pending=None):
    """Serve the app locally and optionally relay this instance over HTTPS."""
    if (form is None) == (chat is None):
        raise ValueError("Supply exactly one function app or chat callback.")
    schema = form.schema() if form is not None else {"title": title, "endpoint": "/reply"}
    page = (files("unique_interface").joinpath("form.html").read_bytes() if form is not None
            else _page(mode="python", title=title).encode())
    if type(concurrency_limit) is not int or concurrency_limit < 1:
        raise ValueError("concurrency_limit must be a positive integer.")
    if max_pending is not None and (type(max_pending) is not int or max_pending < 0):
        raise ValueError("max_pending must be a nonnegative integer.")
    lock = threading.BoundedSemaphore(concurrency_limit)
    admission = (threading.BoundedSemaphore(concurrency_limit + max_pending)
                 if max_pending is not None else None)
    allowed = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, body, kind="application/json", code=200):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def valid(self):
            hosts = {urlsplit(u).netloc for u in tuple(allowed)}
            return self.headers.get("Host") in hosts and (
                not self.headers.get("Origin") or self.headers["Origin"] in allowed)

        def do_GET(self):
            if not self.valid():
                return self.send_error(403)
            if self.path == "/":
                return self.respond(page, "text/html; charset=utf-8")
            if form is not None and self.path in {"/docs", "/client.mjs"}:
                asset, mime = ("api.html", "text/html") if self.path == "/docs" else ("client.mjs", "text/javascript")
                return self.respond(files("unique_interface").joinpath(asset).read_bytes(), mime)
            if self.path == "/health":
                return self.respond(b"unique-interface-ready", "text/plain")
            if self.path == "/api/schema":
                return self.respond(json.dumps(schema).encode())
            self.send_error(404)

        def do_POST(self):
            if not self.valid():
                return self.send_error(403)
            if self.headers.get_content_type() != "application/json":
                return self.send_error(415)
            if admission is not None and not admission.acquire(blocking=False):
                return self.respond(b'{"error":"App is busy. Try again later."}', code=429)
            try:
                self.invoke()
            finally:
                if admission is not None:
                    admission.release()

        def invoke(self):
            event = self.path.removeprefix("/api/")
            is_chat = chat is not None and self.path == "/reply"
            if not is_chat and (form is None or not self.path.startswith("/api/") or event not in form.events):
                return self.send_error(404)
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= (262144 if is_chat else 16 * 1024 * 1024):
                    return self.send_error(413)
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError
                start = time.perf_counter()
                if not is_chat:
                    with lock:
                        output = form.call(event, data["inputs"])
                    result = {"outputs": output, "duration_ms": round(1000*(time.perf_counter()-start), 1)}
                    return self.respond(json.dumps(result, allow_nan=False).encode())
                msg, history = data["message"], data.get("history", [])
                if not isinstance(msg, str) or not msg.strip() or not isinstance(history, list):
                    raise ValueError
                if any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                       or not isinstance(m.get("content"), str) for m in history):
                    raise ValueError
            except (KeyError, ValueError, TypeError):
                return self.respond(b'{"error":"Invalid input or output for this callback."}', code=400)
            except Exception:
                return self.respond(b'{"error":"Callback failed."}', code=500)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def emit(item):
                self.wfile.write((json.dumps(item) + "\n").encode())
                self.wfile.flush()
            try:
                with lock:
                    result = chat(msg, history)
                    if isinstance(result, str):
                        import re
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
                emit({"duration_ms": round(1000*(time.perf_counter()-start), 1)})
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                emit({"error": "The reply callback failed."})

    if space:
        host = os.environ.get("SPACE_HOST", "")
        if not host.endswith(".hf.space") or urlsplit("https://" + host).hostname != host or share:
            raise ValueError("space=True requires a Hugging Face SPACE_HOST and share=False.")
        allowed.add("https://" + host)
    server = ThreadingHTTPServer(("0.0.0.0" if space else "127.0.0.1", port or (7860 if space else 0)), Handler)
    app = App(server)
    allowed.add(app.local_url)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    atexit.register(app.close)
    try:
        print("Local URL:", app.local_url, flush=True)
        if share:
            app._relay, app.share_url = sharing.connect(app.local_url, allowed.add)
            print("Public URL:", app.share_url, flush=True)
        if open_browser and not space:
            webbrowser.open_new_tab(app.local_url)
        if block is None:
            import sys
            block = "ipykernel" not in sys.modules
        if block:
            try:
                while not app._closed:
                    time.sleep(0.2)
            except KeyboardInterrupt:
                app.close()
        return app
    except BaseException:
        app.close()
        raise
