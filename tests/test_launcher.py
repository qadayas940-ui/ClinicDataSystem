"""Desktop startup regression checks using only temporary CI data."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

import launcher


class DesktopLauncherTests(SimpleTestCase):
    def test_client_reuses_cookies_and_starts_in_arabic(self):
        webview = MagicMock()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules, {"webview": webview}), patch.dict(os.environ, {"APPDATA": directory}):
                launcher._open_client("http://127.0.0.1:8765")
            self.assertEqual(webview.create_window.call_args.args[1], "http://127.0.0.1:8765/start/")
            self.assertFalse(webview.start.call_args.kwargs["private_mode"])
            self.assertEqual(
                Path(webview.start.call_args.kwargs["storage_path"]),
                Path(directory) / "ClinicDataSystem" / "WebView",
            )
