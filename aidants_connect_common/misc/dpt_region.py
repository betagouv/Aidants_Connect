#!/usr/bin/env python

import argparse
import json
import os
import sys


def main() -> int:
    try:
        from pandas import read_csv
    except ImportError:
        in_venv = bool(os.getenv("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix
        print(
            "ERREUR: Le paquet 'pandas' n'est pas installé; "
            f"lancez 'pip install {'' if in_venv else '--user'} pandas "
            "et recommancez"
        )
        return 1

    parser = argparse.ArgumentParser(
        description="Moulinette pour transformer un fichier CSV de département "
        "avec leur code INSEE et un fichier CSV de région avec leur "
        "code INSEE en un fichier JSON pour peupler la BDD"
    )
    parser.add_argument(
        "-d",
        "--departments",
        type=argparse.FileType("r"),
        required=True,
        help="Le chemin vers le CSV contenant les départements et leur code INSEE",
    )
    parser.add_argument(
        "-r",
        "--regions",
        type=argparse.FileType("r"),
        required=True,
        help="Le chemin vers le CSV contenant les régions et leur code INSEE",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        required=True,
        help="Le nom du fichier JSON à générer",
    )

    parsed_args = parser.parse_args()

    departments_df = read_csv(parsed_args.departments)
    regions_df = read_csv(parsed_args.regions)

    regions = []
    regions_cache = {}
    for _, item in regions_df.iterrows():
        regions_cache[item["REG"]] = item["LIBELLE"]
        regions.append(
            {
                "name": str(item["LIBELLE"]).strip(),
                "inseeCode": str(item["REG"]).strip(),
            }
        )

    def dataviz_zipcode(zipcode: str):
        zipcode = zipcode.upper()
        if zipcode.startswith("2A") or zipcode.startswith("2B"):
            return "20"
        elif zipcode.startswith("97"):
            return zipcode[:3]

        return zipcode[:2]

    departments = [
        {
            "zipcode": dataviz_zipcode(item["DEP"]),
            "inseeCode": str(item["DEP"]).strip(),
            "name": str(item["LIBELLE"]).strip(),
            "region": regions_cache[item["REG"]],
        }
        for _, item in departments_df.iterrows()
    ]

    with open(parsed_args.out, mode="w") as out:
        json.dump(
            {"regions": regions, "departments": departments},
            out,
            ensure_ascii=False,
            indent=4,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
