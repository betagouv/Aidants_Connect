#!/usr/bin/env python3
"""
Script pour récupérer automatiquement les URLs publiques à tester avec Lighthouse
en analysant les URLs Django avec le resolver
"""
import argparse
import inspect
import os
import re
import sys
from collections import defaultdict

import django
from django.urls import URLPattern, URLResolver, get_resolver

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aidants_connect.settings")

django.setup()


def is_view_protected(view):
    """
    Détermine si une vue nécessite une authentification
    """
    # CBV avec LoginRequiredMixin
    if hasattr(view, "view_class"):
        for base in inspect.getmro(view.view_class):
            if base.__name__ == "LoginRequiredMixin":
                return True
    # login_required sur fonction
    if hasattr(view, "view_is_protected") or getattr(view, "login_required", False):
        return True
    if getattr(view, "__name__", "").startswith("login_required"):
        return True
    return False


def normalize_path(path):
    """
    Nettoie et normalise un path Django pour Lighthouse
    """
    # Supprimer les caractères regex Django
    path = re.sub(r"[\^$]", "", path)

    # Assurer qu'on a un path propre
    if not path.startswith("/"):
        path = "/" + path

    # Supprimer les doubles slashes
    path = re.sub(r"/+", "/", path)

    # Pour la racine, retourner un string vide (sera transformé en / par CircleCI)
    if path == "/":
        return ""

    # Supprimer le slash final pour les autres paths
    return path.rstrip("/")


def is_lighthouse_testable(path):
    """
    Vérifie si un path est testable par Lighthouse
    """
    # Exclure les paths avec des paramètres dynamiques
    if re.search(r"<[^>]+>", path):
        return False

    # Exclure les paths de logout
    if "logout" in path:
        return False

    # Exclure les fichiers statiques
    if any(ext in path for ext in [".ico", ".js", ".css", ".png", ".jpg"]):
        return False

    return True


def list_public_urls(
    urlpatterns,
    prefix="",
    exclude_prefixes=(
        "adm/",
        "__debug__/",
        "api/",
        "sms/",
        "espace-aidant/",
        "espace-responsable/",
        "datapass",
        "usagers/",
        "mandats/",
        "creation_mandat/",
        "renew_mandat/",
        "authorize/",
        "token/",
        "userinfo/",
        "notifications/",
        "select_demarche/",
        "callback/",
        "fc_authorize/",
        "habilitation/nouvelle/",
        "favicon.ico",
        "jsreverse/",
        "formations/",
        "markdown/",
        "activity_check/",
        "logout",
    ),
):
    """
    Récupère toutes les URLs publiques en analysant les patterns Django
    """
    public_urls = []
    for entry in urlpatterns:
        if isinstance(entry, URLPattern):
            full_path = prefix + str(entry.pattern)

            # Normaliser le path
            normalized_path = normalize_path(full_path)

            # Vérifier les exclusions
            if any(
                normalized_path.lstrip("/").startswith(x.rstrip("/"))
                for x in exclude_prefixes
            ):
                continue

            # Vérifier si testable par Lighthouse
            if not is_lighthouse_testable(full_path):
                continue

            callback = entry.callback
            if not is_view_protected(callback):
                # Vérifier que c'est bien une vue de l'application
                modname = getattr(callback, "__module__", "inconnu")
                if (
                    modname.startswith("aidants_connect")
                    and "api" not in modname
                    and "sms" not in modname
                ):
                    public_urls.append((modname, normalized_path))
        elif isinstance(entry, URLResolver):
            public_urls += list_public_urls(
                entry.url_patterns, prefix + str(entry.pattern), exclude_prefixes
            )
    return public_urls


def get_lighthouse_paths(output_format="csv"):
    """
    Retourne les paths publics dans le format demandé
    """
    urls = get_resolver().url_patterns
    public_urls = list_public_urls(urls)

    if output_format == "csv":
        # Format pour CircleCI : paths séparés par virgules
        paths = sorted(list(set(url[1] for url in public_urls)))
        return ",".join(paths)

    elif output_format == "grouped":
        # Format pour debug : groupé par app
        by_app = defaultdict(list)
        for module, url in public_urls:
            by_app[module].append(url)

        result = "Public URLs par application :\n"
        for app, urls in sorted(by_app.items()):
            result += f"\n== {app} ==\n"
            for url in sorted(urls):
                result += f"   {url}\n"
        return result

    else:
        # Format liste simple
        return sorted(list(set(url[1] for url in public_urls)))


def main():
    """
    Point d'entrée principal du script
    """
    parser = argparse.ArgumentParser(
        description="Extrait les URLs publiques pour les tests Lighthouse"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "grouped", "list"],
        default="csv",
        help="Format de sortie (défaut: csv pour CircleCI)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Affiche les détails par application"
    )

    args = parser.parse_args()

    try:
        if args.debug:
            result = get_lighthouse_paths("grouped")
        else:
            result = get_lighthouse_paths(args.format)

        print(result)

    except Exception as e:
        print(f"Erreur lors de l'extraction des URLs: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
