import os
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from _module_loader import load_script_module


gist = load_script_module("gist.py", "gist_script")


class TestGist(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tmpdir.cleanup()

    def _mock_response(self, url):
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"html_url": url}
        return response

    def test_get_gist_url_requires_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(gist, "load_dotenv", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "Missing GITHUB_TOKEN"):
                    gist.get_gist_url("style-a", "print('hello')")

    def test_get_gist_url_reuses_cached_gist_when_source_unchanged(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "token"}):
            response = self._mock_response("https://gist.github.com/example/one")
            with patch.object(gist.requests, "post", return_value=response) as post_mock:
                url_first = gist.get_gist_url("style-a", "print('hello')")
                url_second = gist.get_gist_url("style-a", "print('hello')")

            self.assertEqual(url_first, "https://gist.github.com/example/one")
            self.assertEqual(url_second, "https://gist.github.com/example/one")
            self.assertEqual(post_mock.call_count, 1)

            conn = sqlite3.connect("gists.db")
            row = conn.execute(
                "SELECT url FROM gists WHERE stylename=?", ("style-a",)
            ).fetchone()
            conn.close()
            self.assertEqual(row[0], "https://gist.github.com/example/one")

    def test_get_gist_url_creates_new_gist_when_source_changes(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "token"}):
            response_one = self._mock_response("https://gist.github.com/example/one")
            response_two = self._mock_response("https://gist.github.com/example/two")
            with patch.object(
                gist.requests, "post", side_effect=[response_one, response_two]
            ) as post_mock:
                url_first = gist.get_gist_url("style-a", "print('v1')")
                url_second = gist.get_gist_url("style-a", "print('v2')")

            self.assertEqual(url_first, "https://gist.github.com/example/one")
            self.assertEqual(url_second, "https://gist.github.com/example/two")
            self.assertEqual(post_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
