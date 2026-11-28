import base64
import json
import unittest
from urllib import request, error
from unique_interface import Interface, Blocks, Row, Tab, Textbox, Slider, Button, Upload


class FunctionTests(unittest.TestCase):
    def test_local_http(self):
        app = Interface(lambda s, n: s * int(n), ["text", Slider(1, 5)], "text").launch(
            open_browser=False, block=False)
        self.addCleanup(app.close)
        client = request.build_opener(request.ProxyHandler({}))
        def post(path, body, origin=None):
            headers = {"Content-Type": "application/json"}
            if origin: headers["Origin"] = origin
            return client.open(request.Request(app.local_url+path, data=json.dumps(body).encode(), headers=headers))
        with client.open(app.local_url+"/api/schema") as r:
            self.assertIn("predict", json.load(r)["events"])
        with post("/api/predict", {"inputs": ["a", 3]}) as r:
            result = json.load(r)
            self.assertEqual(result["outputs"], ["aaa"])
            self.assertGreaterEqual(result["duration_ms"], 0)
        with self.assertRaises(error.HTTPError) as ctx: post("/api/predict", {"inputs": ["a", 50]})
        self.assertEqual(ctx.exception.code, 400)
        with self.assertRaises(error.HTTPError) as ctx: post("/api/predict", {"inputs": []}, "https://elsewhere.invalid")
        self.assertEqual(ctx.exception.code, 403)
        self.assertIsNone(app.share_url)

    def test_binary_and_multi_output(self):
        demo = Interface(lambda f: (f.name, Upload(f.name, f.mime, f.data[::-1])), "file", ["text", "file"])
        output = demo.call("predict", [{"name":"a.txt", "mime":"text/plain", "data":"YWJj"}])
        self.assertEqual(output[0], "a.txt")
        self.assertEqual(base64.b64decode(output[1]["data"]), b"cba")

    def test_blocks(self):
        with Blocks("Tools") as demo:
            with Tab("Edit"), Row():
                src, dst = Textbox("Input"), Textbox("Result")
            Button("Uppercase").click(str.upper, src, dst, api_name="upper")
        self.assertEqual(demo.call("upper", ["abc"]), ["ABC"])
        self.assertEqual(demo.schema()["layout"]["children"][0]["type"], "tab")
