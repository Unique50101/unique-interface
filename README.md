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

## Share your own Python function

[Visual documentation and interactive example](https://uniqueopensources.web.app/docs/unique-interface)

```python
from unique_interface import Interface

def greet(name):
    return f"Hello, {name}!"

demo = Interface(greet, inputs="text", outputs="text", title="Greeting demo")
app = demo.launch(share=True)
```

Visitors to the printed public HTTPS URL call **your running function**. Keep the script or notebook runtime running. Each launch receives a local loopback URL. Sharing is opt-in and uses a temporary Cloudflare Quick Tunnel. On first use the package finds cloudflared on PATH or downloads and checksum-verifies the official helper on supported Windows, macOS and Linux systems. The machine must allow the helper to reach Cloudflare. Anyone with the public URL can invoke the callback. For a membership-restricted permanent URL, deploy a private Space. A loopback address on hosted Colab belongs to the runtime machine.

In notebooks, `app.local_url` and `app.share_url` are available on the returned handle. Call `app.close()` to end both routes. In scripts, launch blocks until Ctrl+C. Pass `block=False` to manage the app lifecycle yourself.

```python
from unique_interface import ChatInterface
ChatInterface(lambda message, history: f"You wrote {message}").launch(share=True)
```

### Inputs, outputs and layouts

Supply component types such as `"text"`, `"number"`, `"checkbox"`, `"json"`, `"image"`, `"audio"`, `"video"`, and `"file"`. Use `Slider(1, 5)` for bounded numeric input. Uploaded media arrives as `Upload(name, mime, data)`; return an Upload to display or download generated media. Audio inputs also support microphone recording in compatible browsers with permission. Return a list of numeric values for a `"chart"` line plot. Multiple outputs use a tuple in declared order.

```python
from unique_interface import Blocks, Tab, Row, Textbox, Button
with Blocks("Text tools") as demo:
    with Tab("Uppercase"), Row():
        source = Textbox("Input")
        result = Textbox("Result")
    Button("Convert").click(str.upper, source, result, api_name="upper")
demo.launch()
```

### Call the generated API

`GET /api/schema` describes components and events. POST JSON to `/api/predict` for Interface, or `/api/<api_name>` for a named button callback. Example request: `{"inputs":["Ada"]}`. Example response: `{"outputs":["Hello, Ada!"],"duration_ms":0.4}`. For file inputs send `{"name":"sample.txt","mime":"text/plain","data":"YWJj"}` as the input value. Chat uses `POST /reply` with `{"message":"Hi","history":[]}`, returning newline-delimited JSON. The UI displays elapsed response time for successful runs.

### Permanent Python deployment on Hugging Face

For a server-side Python callback, use a Docker Space if available on your account. For static browser inference, duplicate the UniqueChat Static Space described above. Hugging Face manages the global SDK picker. Unique Interface is installed or exported inside the chosen SDK.

[Copy the Docker Space starter](https://github.com/Unique50101/unique-interface/tree/main/examples/docker-space). Put its README.md, Dockerfile and app.py in the root of your Docker Space and edit `predict`. The starter calls `launch(space=True)` to serve the permanent Space address on port 7860.
