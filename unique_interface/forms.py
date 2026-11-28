"""Declarative inputs, outputs, events and layouts."""
import base64
import contextvars
import math
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_parent = contextvars.ContextVar("unique_layout", default=None)
TYPES = {"text", "number", "slider", "checkbox", "file", "image", "audio", "video", "chart", "json",
         "dropdown", "radio", "checkgroup", "color", "code", "dataframe", "barplot", "scatterplot"}


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

    def _bind(self, trigger, fn, inputs, outputs, api_name):
        parent = _parent.get()
        if not parent or self not in parent[0].fields:
            raise ValueError("Bind the component inside its Blocks layout.")
        app = parent[0]
        name = api_name or f"{trigger}_{len(app.events)}"
        app._event(name, fn, components(inputs), components(outputs))
        app.bindings.append({"field": app.fields[self], "trigger": trigger, "event": name})
        return self

    def change(self, fn, inputs, outputs, *, api_name=None):
        return self._bind("change", fn, inputs, outputs, api_name)

    def submit(self, fn, inputs, outputs, *, api_name=None):
        return self._bind("submit", fn, inputs, outputs, api_name)

    def upload(self, fn, inputs, outputs, *, api_name=None):
        if self.kind not in {"file", "image", "audio", "video"}:
            raise ValueError("Upload events require a file or media field.")
        return self._bind("upload", fn, inputs, outputs, api_name)

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


def LinePlot(label="Line plot"):
    return Chart(label)


def BarPlot(label="Bar plot"):
    return Component("barplot", label)


def ScatterPlot(label="Scatter plot"):
    return Component("scatterplot", label)


def _choices(kind, choices, label):
    values = list(choices)
    if not values or not all(isinstance(v, str) for v in values) or len(set(values)) != len(values):
        raise ValueError("Choices must be distinct strings.")
    return Component(kind, label, choices=values)


def Dropdown(choices, label="Choose an option"):
    return _choices("dropdown", choices, label)


def Radio(choices, label="Choose one"):
    return _choices("radio", choices, label)


def CheckboxGroup(choices, label="Choose options"):
    return _choices("checkgroup", choices, label)


def Dataframe(headers, label="Table"):
    headers = list(headers)
    if not headers or not all(isinstance(h, str) for h in headers):
        raise ValueError("Supply column names.")
    return Component("dataframe", label, headers=headers)


def ColorPicker(label="Color"):
    return Component("color", label)


def Code(label="Code"):
    return Component("code", label)


def components(spec):
    if spec is None:
        return []
    if not isinstance(spec, (list, tuple)):
        spec = [spec]
    return [item if isinstance(item, Component) else Component(item) for item in spec]


def decode(field, value):
    if field.kind in {"dropdown", "radio", "checkgroup"}:
        selected = value if field.kind == "checkgroup" else [value]
        if not isinstance(selected, list) or any(v not in field.options["choices"] for v in selected):
            raise ValueError("Invalid choice.")
    if field.kind == "dataframe":
        width = len(field.options["headers"])
        if not isinstance(value, list) or any(not isinstance(row, list) or len(row) != width for row in value):
            raise ValueError("Rows must match the declared columns.")
    if field.kind == "code" and not isinstance(value, str):
        raise ValueError("Expected a code string.")
    if field.kind == "color":
        import re
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Expected a six-digit hex color.")
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
    if field.kind in {"chart", "barplot"}:
        result = [float(x) for x in value]
        if not all(math.isfinite(x) for x in result):
            raise ValueError("Plot values must be finite.")
        return result
    if field.kind == "scatterplot":
        points = []
        for x, y in value:
            x, y = float(x), float(y)
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError("Plot coordinates must be finite.")
            points.append([x, y])
        return points
    if field.kind == "dataframe":
        return decode(field, value)
    return str(value) if field.kind == "text" else value


class Blocks:
    def __init__(self, title="Unique Interface", *, theme="light"):
        if theme not in {"light", "dark", "auto"}:
            raise ValueError("Use light, dark, or auto.")
        self.theme, self.bindings = theme, []
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
        return {"title": self.title, "layout": self.layout, "theme": self.theme, "bindings": self.bindings,
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
    def __init__(self, fn, inputs="text", outputs="text", title="Unique Interface", *, examples=(), cache_examples=False, theme="light"):
        super().__init__(title, theme=theme)
        ins, outs = components(inputs), components(outputs)
        for c in ins:
            self._add(c, self.layout)
        self.layout["children"].append({"type": "button", "label": "Run", "event": "predict"})
        self._example_cache = {}
        for row in examples:
            if not isinstance(row, (list, tuple)) or len(row) != len(ins):
                raise ValueError("Supply one example value per input.")
            for c, value in zip(ins, row):
                if c.kind in {"file", "image", "audio", "video"}:
                    raise ValueError("File examples require a browser upload.")
                decode(c, value)
            self.layout["children"].append({"type": "example", "values": list(row),
                                            "fields": [self.fields[c] for c in ins]})
        for c in outs:
            self._add(c, self.layout)
        self._event("predict", fn, ins, outs)
        if cache_examples:
            for node in self.layout["children"]:
                if node["type"] == "example":
                    key = self._cache_key(node["values"])
                    self._example_cache[key] = super().call("predict", node["values"])

    @staticmethod
    def _cache_key(values):
        return json.dumps(values, sort_keys=True, allow_nan=False, separators=(",", ":"))

    def call(self, name, values):
        if name == "predict" and self._example_cache:
            from copy import deepcopy
            key = self._cache_key(values)
            if key in self._example_cache:
                return deepcopy(self._example_cache[key])
        return super().call(name, values)


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
def Group(label="Group"): return _layout("group", label)
def Accordion(label): return _layout("accordion", label)
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


class TabbedInterface(Blocks):
    """Compose existing function apps and Blocks without changing their event names."""
    def __init__(self, apps, tab_names, title="Unique Interface", *, theme="light"):
        super().__init__(title, theme=theme)
        apps, names = list(apps), list(tab_names)
        if not apps or len(apps) != len(names):
            raise ValueError("Supply one tab name per app.")
        self._routes = {}
        self._descriptors = {}
        for index, (app, label) in enumerate(zip(apps, names)):
            if not isinstance(app, Blocks):
                raise TypeError("Tabs accept Interface or Blocks apps.")
            prefix = f"tab{index}_"
            schema = app.schema()
            self._descriptors.update({prefix+k: v for k, v in schema["fields"].items()})
            for event, spec in schema["events"].items():
                self._routes[prefix+event] = (app, event)
                self.events[prefix+event] = {key: [prefix+i for i in spec[key]]
                                             for key in ("inputs", "outputs")}
            for binding in schema["bindings"]:
                self.bindings.append(dict(binding, field=prefix+binding["field"],
                                          event=prefix+binding["event"]))
            def remap(node):
                result = dict(node)
                for key in ("id", "event"):
                    if key in result:
                        result[key] = prefix + result[key]
                if "fields" in result:
                    result["fields"] = [prefix+i for i in result["fields"]]
                if "children" in result:
                    result["children"] = [remap(child) for child in result["children"]]
                return result
            self.layout["children"].append({"type": "tab", "label": label,
                                            "children": [remap(schema["layout"])]})

    def schema(self):
        return {"title": self.title, "layout": self.layout, "theme": self.theme,
                "fields": self._descriptors, "bindings": self.bindings, "events": self.events}

    def call(self, name, values):
        app, event = self._routes[name]
        return app.call(event, values)
