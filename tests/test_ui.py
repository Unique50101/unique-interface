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

    def test_stream_and_threads(self):
        def stream(message, history):
            yield "first "
            yield "second"
        app = ChatInterface(stream)
        updates = []
        app.log.observe(lambda event: updates.append(event["new"]), names="value")
        app.prompt.value = "question"
        app.send.click()
        self.assertTrue(any("first " in html and "second" not in html for html in updates))
        self.assertEqual(app.history[-1]["content"], "first second")
        self.assertIn("uc-user", app.log.value)
        self.assertIn("uc-assistant", app.log.value)
        app.new.click()
        self.assertFalse(app.history)
        app._select(0)
        self.assertEqual(app.history[0]["content"], "question")

    def test_word_reveal_and_failed_retry(self):
        app = ChatInterface(lambda *_: "two words")
        app.prompt.value = "question"
        app.send.click()
        self.assertEqual(app.log.value.count('class="uc-word"'), 2)
        def broken(*_):
            yield "partial"
            raise ValueError("failed")
        app.fn = broken
        app.retry.click()
        self.assertEqual(app.history[-1]["content"], "two words")
        self.assertNotIn("partial", app.log.value)
