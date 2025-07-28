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

        # Analyser les résultats par URL
        self._analyze_lighthouse_results(result)

    def _analyze_lighthouse_results(self, result):
        """
        Analyse les résultats Lighthouse et affiche un rapport détaillé
        """
        print("\n" + "=" * 80)
        print("📊 RAPPORT LIGHTHOUSE DÉTAILLÉ")
        print("=" * 80)

        urls = self.lighthouse_config["ci"]["collect"]["url"]
        output = result.stdout + result.stderr

        # Analyser chaque URL
        success_count = 0
        error_count = 0

        for url in urls:
            url_path = url.replace(self.live_server_url, "")

            if f"Running Lighthouse 1 time(s) on {url}" in output:
                if f"{url}\nRun #1...done." in output:
                    print(f"✅ {url_path:<40} - SUCCÈS")
                    success_count += 1
                elif f"{url}\nRun #1...failed!" in output:
                    print(f"❌ {url_path:<40} - ÉCHEC")
                    error_count += 1
                else:
                    print(f"⚠️  {url_path:<40} - STATUT INCONNU")
                    error_count += 1

        print(
            f"""
            📈 RÉSUMÉ : {success_count} succès
            {error_count} erreurs sur {len(urls)} pages
            """
        )

        # Indiquer où trouver les rapports détaillés
        if os.path.exists(".lighthouseci"):
            print("📁 Rapports détaillés : .lighthouseci/")
            # Lister les fichiers HTML générés
            try:
                html_files = [
                    f for f in os.listdir(".lighthouseci") if f.endswith(".html")
                ]
                if html_files:
                    print("📄 Fichiers de rapport HTML :")
                    for html_file in sorted(html_files):
                        print(f"   - .lighthouseci/{html_file}")

            except OSError:
                pass

        print("=" * 80)
