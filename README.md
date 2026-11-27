# Unique Interface

Build a black-and-white chat or file-review panel inside Colab, JupyterLab, or a VS Code Python notebook. Both components use the Unique logo. The package renders through ipywidgets and runs callbacks in the notebook kernel.

```python
%pip install unique-interface
```

```python
from unique_interface import ChatInterface

def reply(message, history):
    return f"You wrote: {message}"

chat = ChatInterface(reply, title="My chat").launch()
```

Chat supports send, retry, clear, and per-instance conversation history. The callback receives the new text and previous messages as role/content dictionaries. Supply your own model or Python function. A failed callback leaves the conversation available for retry.

```python
from unique_interface import FileInterface

def inspect_file(path, folder):
    return f"{path.stat().st_size} bytes received", None

panel = FileInterface(inspect_file, title="Inspect a file").launch()
```

The file callback receives a temporary input path and working directory. Return a plain-text summary and optionally a generated path for download. The input limit defaults to 10 MiB. In Colab enable the custom widget manager before launching. In local JupyterLab or desktop VS Code choose the Python kernel with this package installed.

[Run UniqueChat](https://colab.research.google.com/github/Unique50101/uniquechat/blob/main/UniqueChat.ipynb) · [Run SheetReview](https://colab.research.google.com/github/Unique50101/unique-sheetreview/blob/main/SheetReview.ipynb)
