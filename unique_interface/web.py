"""Full-page chat for local Python and Hugging Face Static Spaces."""
import json
from importlib.resources import files
from pathlib import Path


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


def serve(fn, *, title="UniqueChat", port=0, open_browser=True, share=False, block=None, space=False):
    """Run your chat callback locally and optionally share the running instance."""
    from .runtime import launch
    return launch(chat=fn, title=title, port=port, open_browser=open_browser, share=share, block=block, space=space)
