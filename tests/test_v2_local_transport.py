from __future__ import annotations

import unittest

from driftdoctor.v2 import _validated_ollama_url


class LocalOllamaTransportTests(unittest.TestCase):
    def test_loopback_urls_are_accepted(self) -> None:
        urls = [
            "http://localhost:11434/api/chat",
            "http://127.0.0.1:11434/api/chat",
            "http://127.7.8.9:11434/api/chat",
            "http://[::1]:11434/api/chat",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(_validated_ollama_url(url), url)

    def test_remote_or_ambiguous_urls_are_rejected(self) -> None:
        urls = [
            "https://localhost:11434/api/chat",
            "http://ollama.example.com:11434/api/chat",
            "http://localhost.evil.example:11434/api/chat",
            "http://user:pass@localhost:11434/api/chat",
            "http://localhost:11434/api/generate",
            "http://localhost:11434/api/chat?debug=1",
            "file:///tmp/socket",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                _validated_ollama_url(url)


if __name__ == "__main__":
    unittest.main()
