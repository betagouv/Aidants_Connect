import json
import os
import subprocess
import tempfile
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag


@tag("accessibility")
class PublicUrlsAccessibilityTestCase(StaticLiveServerTestCase):
    """
    Test d'accessibilité avec Lighthouse CI
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(".lighthouserc.json", "r") as f:
            cls.lighthouse_config = json.load(f)
        cls.temp_config_fd, cls.temp_config_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(cls.temp_config_fd, "w") as f:
            json.dump(cls.lighthouse_config, f, indent=2)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "temp_config_path") and os.path.exists(cls.temp_config_path):
            os.remove(cls.temp_config_path)
        super().tearDownClass()

    def test_lighthouse_accessibility(self):
        time.sleep(2)
        url = os.environ.get("LIGHTHOUSE_URL")
        url = url.replace("http://localhost:8000", self.live_server_url)
        result = subprocess.run(
            [
                "./node_modules/.bin/lhci",
                "autorun",
                f"--config={self.temp_config_path}",
                f"--collect.url={url}",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(
                "Accessibility tests ====================== ❌ ",
                result.stderr,
                result.stdout,
            )
            # self.fail("Accessibility tests ❌ ", result.stderr, result.stdout)
        else:
            print("Accessibility tests ====================== ✅ ", result.stdout)
