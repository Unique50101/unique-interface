import unittest
from unique_interface import ChatInterface, FileInterface


class Interfaces(unittest.TestCase):
    def test_chat(self):
        calls = []
        def answer(message, history):
            calls.append((message, history))
            return "<hello>"
        ui = ChatInterface(answer)
        ui.prompt.value = "Hi"
        ui.send.click()
        ui.prompt.value = "Again"
        ui.send.click()
        ui.retry.click()
        self.assertEqual(len(ui.history), 4)
        self.assertEqual(len(calls[-1][1]), 2)
        self.assertIn("&lt;hello&gt;", ui.log.value)
        ui.clear.click()
        self.assertFalse(ui.history)

    def test_file(self):
        from datetime import datetime, timezone
        def review(path, folder):
            out = folder / "copy.csv"
            out.write_bytes(path.read_bytes())
            return "<done>", out
        ui = FileInterface(review)
        ui.upload.value = (dict(name="demo.csv", size=3, type="text/csv",
                                content=memoryview(b"a,b"),last_modified=datetime.now(timezone.utc)),)
        ui.run.click()
        self.assertIn("&lt;done&gt;", ui.result.value)
        self.assertIn('download="copy.csv"', ui.result.value)
