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
    Utilise le même framework que les tests Selenium pour garantir
    que Django démarre correctement avec toutes les dépendances mockées
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

        # Remplacer localhost:8000 par l'URL du serveur de test
        if "ci" in self.lighthouse_config and "collect" in self.lighthouse_config["ci"]:
            collect_config = self.lighthouse_config["ci"]["collect"]

            # Remplacer les URLs
            if "url" in collect_config:
                collect_config["url"] = [
                    url.replace("http://localhost:8000", self.live_server_url)
                    for url in collect_config["url"]
                ]

            # Supprimer les commandes de serveur car Django est déjà démarré
            collect_config.pop("startServerCommand", None)
            collect_config.pop("startServerReadyPattern", None)
            collect_config.pop("startServerReadyTimeout", None)

        # Créer un fichier de configuration temporaire
        self.temp_config_fd, self.temp_config_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(self.temp_config_fd, "w") as f:
            json.dump(self.lighthouse_config, f, indent=2)

    def tearDown(self):
        """
        Nettoie le fichier de configuration temporaire
        """
        super().tearDown()
        if hasattr(self, "temp_config_path") and os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)

    def test_lighthouse_accessibility(self):
        """
        Lance Lighthouse CI contre le serveur de test Django
        """
        # Attendre que le serveur soit prêt
        time.sleep(2)

        print(f"🚀 Serveur de test Django démarré sur : {self.live_server_url}")
        urls_count = len(self.lighthouse_config["ci"]["collect"]["url"])
        print(f"📋 URLs à tester : {urls_count} pages")

        # Lancer Lighthouse CI avec la configuration modifiée
        result = subprocess.run(
            ["lhci", "autorun", f"--config={self.temp_config_path}"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Faire échouer le test si les assertions Lighthouse échouent
        if result.returncode != 0:
            self.fail(result.stderr)
        else:
            print("✅ Tests d'accessibilité Lighthouse réussis")
