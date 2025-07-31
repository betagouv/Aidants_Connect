import json
import os
import subprocess
import tempfile
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag


@tag("accessibility")
class LighthouseAccessibilityTestCase(StaticLiveServerTestCase):
    """
    Test d'accessibilité avec Lighthouse CI
    """

    def setUp(self):
        """
        Configure Lighthouse en chargeant .lighthouserc.json et en remplaçant
        localhost:8000 par l'URL du serveur de test Django
        """
        super().setUp()

        # Charger la configuration Lighthouse existante
        with open(".lighthouserc.json", "r") as f:
            self.lighthouse_config = json.load(f)

        # Créer un fichier de configuration temporaire
        self.temp_config_fd, self.temp_config_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(self.temp_config_fd, "w") as f:
            json.dump(self.lighthouse_config, f, indent=2)

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "temp_config_path") and os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)

    def test_lighthouse_accessibility(self):
        # Attendre que le serveur soit prêt
        time.sleep(2)

        url = os.environ.get("LIGHTHOUSE_URL")
        url = url.replace("http://localhost:8000", self.live_server_url)
        # Lancer Lighthouse CI avec la configuration modifiée
        # Utiliser le chemin relatif qui fonctionne en local et en CI
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
            print("Accessibility tests ====================== ❌ ", result.stderr)
            print("=============================================", result.stdout)
        else:
            print("Accessibility tests ====================== ✅ ", result.stdout)
