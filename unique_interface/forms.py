"""Declarative inputs, outputs, events and layouts."""
import base64
import contextvars
import math
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_parent = contextvars.ContextVar("unique_layout", default=None)
TYPES = {"text", "number", "slider", "checkbox", "file", "image", "audio", "video", "chart", "json"}


@dataclass(frozen=True)
class Upload:
    name: str
    mime: str
    data: bytes


class Component:
    def __init__(self, kind, label=None, **options):
        if kind not in TYPES:
            raise ValueError(f"Unknown component: {kind}")
        self.kind, self.label, self.options = kind, label or kind.title(), options
        parent = _parent.get()
        if parent:
            parent[0]._add(self, parent[1])

    def descriptor(self):
        return {"type": self.kind, "label": self.label, **self.options}


def Textbox(label="Text"): return Component("text", label)
def Slider(minimum=0, maximum=100, step=1, label="Value"):
    if not minimum < maximum or step <= 0:
        raise ValueError("Check slider bounds and step.")
    return Component("slider", label, min=minimum, max=maximum, step=step)
def File(label="File"): return Component("file", label)
def Image(label="Image"): return Component("image", label)
def Audio(label="Audio"): return Component("audio", label)
def Video(label="Video"): return Component("video", label)
def Chart(label="Chart"): return Component("chart", label)


def components(spec):
    if spec is None:
        return []
    if not isinstance(spec, (list, tuple)):
        spec = [spec]
    return [item if isinstance(item, Component) else Component(item) for item in spec]


def decode(field, value):
    if field.kind in {"file", "image", "audio", "video"}:
        if not isinstance(value, dict) or not isinstance(value.get("data"), str):
            raise ValueError(f"Choose a file for {field.label}.")
        return Upload(Path(str(value.get("name", "upload"))).name, str(value.get("mime", "")),
                      base64.b64decode(value["data"], validate=True))
    if field.kind in {"number", "slider"}:
        n = float(value)
        if not math.isfinite(n) or field.kind == "slider" and not field.options.get("min", 0) <= n <= field.options.get("max", 100):
            raise ValueError("Number outside the supported range.")
        return n
    if field.kind == "checkbox":
        if not isinstance(value, bool):
            raise ValueError("Expected a boolean.")
        return value
    if field.kind == "text" and not isinstance(value, str):
        raise ValueError("Expected text.")
    return value


def encode(field, value):
    if field.kind in {"file", "image", "audio", "video"}:
        if not isinstance(value, Upload):
            raise ValueError("Return Upload(name, mime, data) for binary output.")
        return {"name": value.name, "mime": value.mime, "data": base64.b64encode(value.data).decode()}
    if field.kind == "chart":
        return [float(x) for x in value]
    return str(value) if field.kind == "text" else value


class Blocks:
    def __init__(self, title="Unique Interface"):
        self.title, self.events, self.fields = title, {}, {}
        self.layout = {"type": "column", "children": []}

    def __enter__(self):
        self._token = _parent.set((self, self.layout))
        return self

    def __exit__(self, *args):
        _parent.reset(self._token)

    def _add(self, comp, node):
        if comp not in self.fields:
            self.fields[comp] = str(len(self.fields))
        node["children"].append({"type": "field", "id": self.fields[comp]})

    def _event(self, name, fn, ins, outs):
        if name in self.events:
            raise ValueError("Duplicate event name.")
        if any(c not in self.fields for c in ins + outs):
            raise ValueError("Create all components inside this Blocks layout.")
        self.events[name] = fn, ins, outs

    def schema(self):
        return {"title": self.title, "layout": self.layout,
                "fields": {i: c.descriptor() for c, i in self.fields.items()},
                "events": {name: {"inputs": [self.fields[c] for c in ins], "outputs": [self.fields[c] for c in outs]}
                           for name, (_, ins, outs) in self.events.items()}}

    def call(self, name, values):
        fn, ins, outs = self.events[name]
        if not isinstance(values, list) or len(ins) != len(values):
            raise ValueError("Wrong number of inputs.")
        result = fn(*(decode(c, v) for c, v in zip(ins, values)))
        result = [result] if len(outs) == 1 else ([] if not outs else result)
        if not isinstance(result, (list, tuple)) or len(result) != len(outs):
            raise ValueError("Callback returned the wrong number of outputs.")
        return [encode(c, v) for c, v in zip(outs, result)]

    def launch(self, **options):
        from .runtime import launch
        return launch(form=self, **options)


class Interface(Blocks):
    def __init__(self, fn, inputs="text", outputs="text", title="Unique Interface"):
        super().__init__(title)
        ins, outs = components(inputs), components(outputs)
        for c in ins:
            self._add(c, self.layout)
        self.layout["children"].append({"type": "button", "label": "Run", "event": "predict"})
        for c in outs:
            self._add(c, self.layout)
        self._event("predict", fn, ins, outs)


@contextmanager
def _layout(kind, label=""):
    app, parent = _parent.get() or (None, None)
    if app is None:
        raise ValueError("Use this layout inside Blocks.")
    child = {"type": kind, "label": label, "children": []}
    parent["children"].append(child)
    token = _parent.set((app, child))
    try:
        yield
    finally:
        _parent.reset(token)


def Row(): return _layout("row")
def Column(): return _layout("column")
def Tab(label): return _layout("tab", label)


class Button:
    def __init__(self, label="Run"):
        self.app, parent = _parent.get() or (None, None)
        if self.app is None:
            raise ValueError("Use Button inside Blocks.")
        self.node = {"type": "button", "label": label}
        parent["children"].append(self.node)

    def click(self, fn, inputs, outputs, *, api_name="predict"):
        self.app._event(api_name, fn, components(inputs), components(outputs))
        self.node["event"] = api_name
        return self
