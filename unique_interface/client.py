"""Python client for Unique Interface function apps."""
import json
from urllib.parse import quote
from urllib.request import Request, urlopen


class Client:
    def __init__(self, url, *, timeout=30):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def schema(self):
        with urlopen(self.url + "/api/schema", timeout=self.timeout) as response:
            return json.load(response)

    def predict(self, *inputs, api_name="predict"):
        body = json.dumps({"inputs": inputs}, allow_nan=False).encode()
        request = Request(self.url + "/api/" + quote(api_name, safe=""), data=body,
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            return json.load(response)
