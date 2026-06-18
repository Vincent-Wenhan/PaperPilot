from __future__ import annotations

import threading
import unittest

from ui.progress import ThreadSafeProgress


class ThreadSafeProgressTests(unittest.TestCase):
    def test_background_thread_records_without_rendering(self) -> None:
        rendered: list[str] = []
        progress = ThreadSafeProgress("Progress", rendered.append)

        progress("main step")

        worker = threading.Thread(target=lambda: progress("worker step"))
        worker.start()
        worker.join()

        self.assertEqual(len(rendered), 1)
        self.assertIn("main step", rendered[0])
        self.assertIn("worker step", progress.markdown())

        progress.render()
        self.assertEqual(len(rendered), 2)
        self.assertIn("worker step", rendered[-1])


if __name__ == "__main__":
    unittest.main()
