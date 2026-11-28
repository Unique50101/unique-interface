# Unique Interface

A compact, monochrome interface for Python chat and file-review tools. The notebook chat is centered and capped at 800 px, with a 144 px conversation sidebar on larger screens. User prompts appear on the right, answers on the left. Press **Enter** to send. Retry replaces the last answer, and New chat starts a separate conversation in the current session.

[Try the public UniqueChat Space](https://huggingface.co/spaces/unique50101/UniqueChat) · [Open UniqueChat in Colab](https://colab.research.google.com/github/Unique50101/uniquechat/blob/main/UniqueChat.ipynb) · [Open SheetReview in Colab](https://colab.research.google.com/github/Unique50101/unique-sheetreview/blob/main/SheetReview.ipynb)

## Install by name

In Colab, Jupyter or a VS Code notebook, run:

```python
%pip -q install --upgrade unique-interface
```

In a terminal, run `python -m pip install --upgrade unique-interface`. Restart an already-running kernel if it imported an older release before the upgrade.

## Show a notebook chat

```python
from unique_interface import ChatInterface

def answer(message, history):
    return f"You wrote: {message}"

chat = ChatInterface(answer, title="My chat").launch()
```

The example echoes text. Replace the callback with your model function to generate answers. It receives the current message and earlier role/content dictionaries. Return a string for a word-by-word reveal, or yield text chunks for live generation. In Colab, enable widgets before launch with `from google.colab import output` and `output.enable_custom_widget_manager()`.

## Open a full-page chat from a Python script

```python
from unique_interface import serve

def answer(message, history):
    return f"You wrote: {message}"

serve(answer, title="My chat")
```

Run the script on your computer. A new browser tab opens at the printed loopback URL. Each tab keeps its conversation in memory. Stop the server with Ctrl+C. The full-page composer supports Enter to send and Shift+Enter for a new line. A hosted Colab runtime has its own loopback address, so use the inline widget or a deployed Space there.

## Share a public or restricted URL

The public demo can be opened in a new tab or shared. To host your own copy, open the demo and choose **Duplicate this Space** from its menu. Choose **Public** for a shareable link or **Private** to let Hugging Face restrict access to authorized members. Each visitor starts their own conversation. Sharing a deployment link does not share a transcript.

To display links to your deployments in a notebook:

```python
chat.set_links(
    public_url="https://huggingface.co/spaces/unique50101/UniqueChat",
    private_url="https://huggingface.co/spaces/YOUR-ORG/YOUR-PRIVATE-SPACE",
)
```

Replace the private URL with an actual access-controlled deployment or omit it. The link label alone grants no access control.

## Build a Hugging Face Static Space with your model

```python
from unique_interface import export_space

export_space("index.html", model="HuggingFaceTB/SmolLM2-135M-Instruct", title="My chat")
```

Run this in an empty directory, create a **Static → Blank** Space, and upload the generated index.html as its entry page. The exported app uses the bundled Unique Interface layout. It loads Transformers.js and a compatible ONNX text-generation model with a chat template and q4 weights into the visitor's browser. The first model load needs internet. For a Python-only model, use the Python callback in your own Python runtime. Static hosting runs JavaScript inference and does not execute Python callbacks.

## Review and download a file

```python
from unique_interface import FileInterface

def inspect_file(path, folder):
    return f"Received {path.stat().st_size} bytes", None

review = FileInterface(inspect_file, title="Inspect a file").launch()
```

Return a plain-text summary and an optional generated file path to show a download link. The default input limit is 10 MiB. SheetReview's notebook provides a complete CSV/XLSX example.
