"""Unique's notebook-native chat and file interfaces."""
from base64 import b64encode
from html import escape
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

import ipywidgets as w
from IPython.display import display

_STYLE = """
.unique-panel{background:white!important;color:#171717!important;border:1px solid #aaa;border-radius:14px;padding:14px;max-width:780px;width:100%!important;box-sizing:border-box;font-family:system-ui,sans-serif}
.unique-panel .widget-button{border-radius:6px;color:#111;background:white;border:1px solid #777}
.unique-panel .unique-primary,.unique-panel .unique-primary button{background:#151515!important;color:white!important}
.unique-panel textarea{background:white!important;color:#151515!important;border:1px solid #777!important;border-radius:6px}
.unique-panel .widget-html{color:#171717}
"""


def _heading(title):
    logo = files("unique_interface").joinpath("logo.b64").read_text().strip()
    return w.HTML(f'<style>{_STYLE}</style><div style="background:#111;color:white;border-radius:8px;display:flex;align-items:center;gap:14px;padding:8px 14px">'
                  f'<img src="data:image/png;base64,{logo}" alt="Unique" width="66" height="66" style="object-fit:contain">'
                  f'<strong style="font:600 19px system-ui">{escape(title)}</strong></div>')


def _panel(*items):
    return w.VBox(items, layout=w.Layout(width="100%")).add_class("unique-panel")


def _button(label, primary=False):
    b = w.Button(description=label, layout=w.Layout(width="auto"))
    if primary:
        b.add_class("unique-primary")
        b.style.button_color = "#151515"
        b.style.text_color = "white"
    return b


class ChatInterface:
    """Display a text chat. fn(message, history) returns the next reply."""

    def __init__(self, fn, *, title="Unique Chat"):
        self.fn = fn
        self.history = []
        self.log = w.HTML()
        self.prompt = w.Textarea(placeholder="Type your message…", layout=w.Layout(width="100%"))
        self.status = w.Label()
        self.send = _button("Send", True)
        self.retry = _button("Retry last reply")
        self.clear = _button("Clear chat")
        self.send.on_click(lambda _: self._respond(False))
        self.retry.on_click(lambda _: self._respond(True))
        self.clear.on_click(lambda _: self.reset())
        self.widget = _panel(_heading(title), self.log, self.prompt,
                             w.HBox([self.send, self.retry, self.clear]), self.status)
        self._render()

    def _render(self):
        rows = []
        for item in self.history:
            who = "You" if item["role"] == "user" else "Unique"
            rows.append(f'<div style="padding:8px 0;border-bottom:1px solid #ddd"><b>{who}</b>'
                        f'<div style="white-space:pre-wrap;overflow-wrap:anywhere">{escape(item["content"])}</div></div>')
        self.log.value = "".join(rows)
        self.retry.disabled = not self.history

    def reset(self):
        self.history.clear()
        self.prompt.value = self.status.value = ""
        self._render()

    def _respond(self, retry):
        if retry and not self.history:
            return
        message = self.history[-2]["content"] if retry else self.prompt.value.strip()
        if not message:
            self.status.value = "Enter a message first."
            return
        prior = self.history[:-2] if retry else self.history[:]
        self.send.disabled = self.clear.disabled = self.retry.disabled = True
        self.status.value = "Generating reply…"
        try:
            reply = self.fn(message, [dict(m) for m in prior])
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("The callback must return a nonempty reply.")
            self.history = prior + [dict(role="user", content=message), dict(role="assistant", content=reply)]
            if not retry:
                self.prompt.value = ""
            self.status.value = ""
        except Exception as exc:
            self.status.value = str(exc)
        finally:
            self.send.disabled = self.clear.disabled = False
            self._render()

    def launch(self):
        display(self.widget)
        return self


class FileInterface:
    """fn(path, directory) returns (plain-text report, optional output path)."""

    def __init__(self, fn, *, title="Unique File Review", accept=".csv,.xlsx", max_bytes=10*1024*1024):
        self.fn, self.max_bytes = fn, max_bytes
        self.upload = w.FileUpload(accept=accept, multiple=False)
        self.run = _button("Review file", True)
        self.result = w.HTML()
        self.run.on_click(lambda _: self._review())
        self.widget = _panel(_heading(title), self.upload, self.run, self.result)

    def _review(self):
        selected = self.upload.value
        if not selected:
            self.result.value = "Choose a file first."
            return
        self.run.disabled = True
        try:
            name, data = selected[0]["name"], selected[0]["content"]
            if len(data) > self.max_bytes:
                raise ValueError("Choose a smaller file.")
            with TemporaryDirectory() as work:
                folder = Path(work)
                source = folder / ("input" + Path(name).suffix.lower())
                source.write_bytes(data)
                summary, output = self.fn(source, folder)
                result = f'<pre style="white-space:pre-wrap">{escape(str(summary))}</pre>'
                if output is not None:
                    output = Path(output)
                    payload = b64encode(output.read_bytes()).decode()
                    result += f'<a style="color:#111;text-decoration:underline" download="{escape(output.name)}" href="data:application/octet-stream;base64,{payload}">Download {escape(output.name)}</a>'
                self.result.value = result
        except Exception as exc:
            self.result.value = escape(str(exc))
        finally:
            self.run.disabled = False

    def launch(self):
        display(self.widget)
        return self
