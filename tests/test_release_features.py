import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from unique_interface import (Blocks, Interface, TabbedInterface, Dropdown, Radio, CheckboxGroup,
                              Textbox, Dataframe, ScatterPlot, Accordion, Client)


class ReleaseFeatures(unittest.TestCase):
    def start(self, demo, **options):
        app = demo.launch(block=False, open_browser=False, **options)
        self.addCleanup(app.close)
        return app

    def test_namespaced_tabs_and_bindings(self):
        with Blocks() as form, Accordion("Options"):
            src, dst = Dropdown(["a", "b"]), Textbox()
            src.change(str.upper, src, dst, api_name="upper")
        app = TabbedInterface([form, form], ["One", "Two"])
        schema = app.schema()
        self.assertEqual(len(schema["bindings"]), 2)
        self.assertEqual(schema["bindings"][1]["event"], "tab1_upper")
        self.assertEqual(app.call("tab1_upper", ["b"]), ["B"])
        with self.assertRaises(ValueError):
            app.call("tab1_upper", ["c"])

    def test_tables_plots_and_choices(self):
        demo = Interface(lambda mode, tags, rows: [[i, float(row[0])] for i,row in enumerate(rows)],
                         [Radio(["Sum"]), CheckboxGroup(["on"]), Dataframe(["Value"])], ScatterPlot())
        self.assertEqual(demo.call("predict", ["Sum",["on"],[["4"]]]), [[[0,4]]])
        for args in [["Sum",["other"],[]], ["Sum",[],[["a","b"]]]]:
            with self.assertRaises(ValueError):
                demo.call("predict", args)

    def test_example_cache_and_real_client(self):
        calls = []
        def echo(value):
            calls.append(value)
            return value
        app = self.start(Interface(echo, examples=[["sample"]], cache_examples=True))
        client = Client(app.local_url)
        self.assertIn("predict",client.schema()["events"])
        self.assertEqual(client.predict("sample")["outputs"], ["sample"])
        self.assertEqual(client.predict("other")["outputs"], ["other"])
        self.assertEqual(calls, ["sample","other"])
        for path in ["/client.mjs","/docs"]:
            with urlopen(app.local_url+path) as response:
                self.assertEqual(response.status, 200)

    def test_bounded_admission(self):
        entered, release = threading.Event(), threading.Event()
        def wait(value):
            entered.set()
            release.wait(5)
            return value
        client = Client(self.start(Interface(wait), max_pending=0).local_url)
        worker = threading.Thread(target=client.predict, args=("first",))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaises(HTTPError) as error:
                client.predict("second")
            self.assertEqual(error.exception.code, 429)
        finally:
            release.set()
            worker.join(5)
