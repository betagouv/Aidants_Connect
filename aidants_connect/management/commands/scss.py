import os
from pathlib import Path
from shutil import which

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generate CSS files from SCSS sources"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Continue compiling stylesheets whenever a source file changes",
        )

    def handle(self, *args, **options):
        action = ""
        if options["watch"]:
            action = "--watch"
        self.check_sass_version()
        self.compile_stylesheets(action)

    def check_sass_version(self):
        if which("sass") is None:
            raise CommandError(
                "You need to install sass before using this command.\n"
                "Check https://sass-lang.com/install"
            )
        sass_version = os.popen("sass --version").read().strip()
        self.stdout.write(f"You are using Sass version {sass_version}.")
        if "Ruby" in sass_version:
            self.stdout.write("Warning! This is an old version of Sass.")
        self.write_horizontal_line()

    def compile_stylesheets(self, action):
        folders = " ".join(
            [
                f"{app}/static/scss/:{app}/static/css/"
                for app in apps.app_configs.keys()
                if (
                    app.startswith("aidants_connect")
                    and Path(f"{app}/static/scss/").exists()
                )
            ]
        )
        command = (
            f"sass {action} --style compressed {folders} "
            "--load-path aidants_connect_common/static/scss/"
        )
        self.stdout.write(f"Running {command}")
        self.write_horizontal_line()
        os.system(command)

    def write_horizontal_line(self):
        self.stdout.write("-" * 15)
