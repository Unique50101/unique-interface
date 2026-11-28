"""Unique's notebook-native chat and file interfaces."""
from time import perf_counter
import re
from collections.abc import Iterator
from base64 import b64encode
from html import escape
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import ipywidgets as w
from IPython.display import display
from .web import export_space, serve
from .forms import Interface, Blocks, Row, Column, Tab, Button, Component, Textbox, Slider, File, Image, Audio, Video, Chart, Upload

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


_CHAT_STYLE = """
.unique-chat {width:100%;max-width:800px;margin-inline:auto;height:clamp(390px,74vh,740px);background:#101010;color:#eee;
 border:1px solid #353535;border-radius:14px;overflow:hidden;container-type:inline-size;font:14px/1.55 system-ui,sans-serif}
.unique-chat .widget-html,.unique-chat .widget-label,.unique-chat .widget-html-content {color:inherit;margin:0}
.unique-chat .widget-button {background:#252525;color:#eee;border:1px solid #444;border-radius:9px;margin:0;padding:0 12px}
.unique-chat .widget-button:hover {background:#363636}
.unique-chat .widget-button:focus-visible {outline:2px solid #fff;outline-offset:-3px}
.unique-chat .widget-button:disabled {opacity:.5}
.unique-chat .uc-sidebar {background:#171717;border-right:1px solid #303030;padding:14px;gap:10px;overflow:auto;width:144px;flex:none}
.unique-chat .uc-brand {display:flex;align-items:center;gap:7px;font-weight:600}
.unique-chat .uc-brand img {width:52px;height:42px;object-fit:contain}
.unique-chat .uc-threadlist {gap:4px}
.unique-chat .uc-threadlist button {text-align:left;overflow:hidden;text-overflow:ellipsis;border:0;background:transparent}
.unique-chat .uc-threadlist .uc-active {background:#303030}
.unique-chat .uc-main {flex:1;min-width:0;padding:12px 16px;gap:9px}
.unique-chat .uc-title {overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-bottom:1px solid #303030;padding:3px 0 10px;font-weight:600}
.unique-chat .uc-log {flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column-reverse}
.unique-chat .uc-log .widget-html-content {width:100%}
.unique-chat .uc-messages,.unique-chat .uc-compose {width:100%;max-width:600px;margin:auto;box-sizing:border-box}
.unique-chat .uc-message {width:fit-content;max-width:100%;box-sizing:border-box;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0 22px;color:#f4f4f4}
.unique-chat .uc-user {margin-left:auto;max-width:82%;padding:10px 16px;background:#303030;border-radius:18px}
.unique-chat .uc-assistant {margin-right:auto;padding:0 4px}
.unique-chat .uc-compose {background:#212121;border:1px solid #434343;border-radius:18px;padding:8px;align-items:center;gap:8px}
.unique-chat .uc-compose .widget-text {flex:1;min-width:0;margin:0}
.unique-chat .uc-compose input {width:100%;height:45px;resize:none;background:#212121;color:white;border:0;padding:7px;font:inherit}
.unique-chat .uc-compose button {color:#111;background:white;border-radius:20px}
.unique-chat .uc-tools {gap:6px;align-items:center;flex-wrap:wrap}
.unique-chat .uc-status {white-space:normal;height:auto}
.unique-chat .uc-word {animation:uc-reveal 1ms step-end both;animation-delay:var(--uc-delay)}
@keyframes uc-reveal {from{opacity:0}to{opacity:1}}
@media(prefers-reduced-motion:reduce){.unique-chat .uc-word{animation:none}}
@container(max-width:590px){.unique-chat .uc-sidebar{width:112px;padding:6px}.unique-chat .uc-main{padding:8px}.unique-chat .uc-brand span{display:none}.unique-chat .uc-user{max-width:92%}}
"""


class ChatInterface:
    """Notebook chat. The callback returns a string or yields text chunks."""

    def __init__(self, fn, *, title="Unique Chat", word_delay=0.035, public_url=None, private_url=None):
        self.title = title
        self.fn = fn
        self.word_delay = max(0.0, float(word_delay))
        self._threads = [[]]
        self._index = 0
        self.history = self._threads[0]
        self._busy = False
        logo = files("unique_interface").joinpath("logo.b64").read_text().strip()
        brand = w.HTML(f'<style>{_CHAT_STYLE}</style><div class="uc-brand"><img alt="Unique" src="data:image/png;base64,{logo}"><span>{escape(title)}</span></div>')
        self.new = _button("New chat")
        self.new.on_click(lambda _: self.new_chat())
        self._links = w.VBox().add_class("uc-threadlist")
        sidebar = w.VBox([brand, self.new, self._links]).add_class("uc-sidebar")
        self._title = w.HTML()
        self.log = w.HTML().add_class("uc-log")
        self.prompt = w.Text(placeholder="Message Unique…", continuous_update=True)
        self.status = w.Label().add_class("uc-status")
        self.send = _button("Send")
        self.retry = _button("Retry last reply")
        self.clear = _button("Clear chat")
        self.send.on_click(lambda _: self._respond(False))
        self.prompt.on_submit(lambda _: self._respond(False))
        self.retry.on_click(lambda _: self._respond(True))
        self.clear.on_click(lambda _: self.reset())
        composer = w.HBox([self.prompt, self.send]).add_class("uc-compose")
        actions = w.HBox([self.retry, self.clear, self.status]).add_class("uc-tools")
        self.links = w.HTML()
        self.set_links(public_url=public_url, private_url=private_url)
        main = w.VBox([self._title, self.links, self.log, actions, composer]).add_class("uc-main")
        self.widget = w.HBox([sidebar, main]).add_class("unique-chat")
        self._refresh()

    def set_links(self, *, public_url=None, private_url=None):
        """Link to existing deployments. Access is enforced by the host."""
        items = []
        for label, url in (("Open public chat", public_url), ("Open private chat", private_url)):
            if url:
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError("Use a full HTTP or HTTPS deployment URL without credentials.")
                items.append(f'<a style="color:inherit" target="_blank" rel="noopener noreferrer" href="{escape(url)}">{label} ↗</a>')
        self.links.value = " &nbsp; ".join(items)
        self.links.layout.display = "" if items else "none"
        return self

    def _select(self, index):
        if self._busy:
            return
        self._index = index
        self.history = self._threads[index]
        self.prompt.value = self.status.value = ""
        self._refresh()

    def new_chat(self):
        if self._busy:
            return
        if self.history:
            self._threads.append([])
            self._select(len(self._threads) - 1)

    def reset(self):
        if not self._busy:
            self.history.clear()
            self._select(self._index)

    def _refresh(self, animate=False):
        links = []
        for i, thread in enumerate(self._threads):
            label = " ".join(thread[0]["content"].split())[:60] if thread else "New conversation"
            link = _button(label)
            if i == self._index:
                link.add_class("uc-active")
                self._title.value = f'<div class="uc-title">{escape(label)}</div>'
            link.on_click(lambda _, index=i: self._select(index))
            links.append(link)
        self._links.children = tuple(reversed(links))
        self.retry.disabled = self.clear.disabled = not self.history
        self._render(self.history, animate)

    def _render(self, messages, animate=False):
        rows = []
        for i, message in enumerate(messages):
            role = message["role"]
            content = message["content"]
            body = escape(content)
            if animate and role == "assistant" and i == len(messages) - 1 and self.word_delay:
                # Whitespace belongs to the original response, including code indentation.
                parts = re.findall(r'\s+|\S+\s*', content)
                interval = min(self.word_delay, 8 / max(1, len(parts)))
                body = "".join(f'<span class="uc-word" style="--uc-delay:{j*interval:.4f}s">{escape(part)}</span>'
                               for j, part in enumerate(parts))
            speaker = "You" if role == "user" else "Unique"
            rows.append(f'<div class="uc-message uc-{role}" aria-label="{speaker}">{body}</div>')
        self.log.value = '<div class="uc-messages">' + "".join(rows) + '</div>'

    def _respond(self, retry):
        if self._busy or (retry and not self.history):
            return
        message = self.history[-2]["content"] if retry else self.prompt.value.strip()
        if not message:
            self.status.value = "Enter a message first."
            return
        prior = self.history[:-2] if retry else self.history[:]
        pending = prior + [dict(role="user", content=message)]
        self._busy = self.new.disabled = self.send.disabled = self.retry.disabled = self.clear.disabled = True
        started = perf_counter()
        self.status.value = "Generating reply…"
        self._render(pending)
        animate = False
        try:
            result = self.fn(message, [dict(m) for m in prior])
            if isinstance(result, str):
                reply = result
                animate = True
            elif isinstance(result, Iterator):
                reply = ""
                for chunk in result:
                    if not isinstance(chunk, str):
                        raise TypeError("Each reply chunk must be text.")
                    if chunk:
                        reply += chunk
                        self._render(pending + [dict(role="assistant", content=reply)])
            else:
                raise TypeError("Return a reply string or yield text chunks.")
            if not reply.strip():
                raise ValueError("The callback returned an empty reply.")
            self.history[:] = pending + [dict(role="assistant", content=reply)]
            if not retry:
                self.prompt.value = ""
            self.status.value = f"Response time: {perf_counter()-started:.2f} s"
        except Exception as exc:
            self.status.value = str(exc)
        finally:
            self._busy = self.new.disabled = self.send.disabled = False
            self._refresh(animate)

    def launch(self, *, share=False, **options):
        if share or options:
            return serve(self.fn, title=self.title, share=share, **options)
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



from .forms import Dropdown, Radio, CheckboxGroup, Dataframe, ColorPicker, Code, Accordion, Group, TabbedInterface
from .client import Client
from .forms import LinePlot, BarPlot, ScatterPlot
