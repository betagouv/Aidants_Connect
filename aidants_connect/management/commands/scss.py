import os
import subprocess
from pathlib import Path
from shutil import which

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils.functional import cached_property


class Command(BaseCommand):
    help = "Generate CSS files from SCSS sources"

    @cached_property
    def sass_command(self):
        # Try command included in node_modules first. The file may not necessarily be
        # executable so we need to test it with `subprocess.run`. `shutils.which`
        # won't detect it.
        import aidants_connect

        node_modules_exe = (
            Path(aidants_connect.__path__[0]).parent / "node_modules" / ".bin" / "sass"
        )

        if not node_modules_exe.exists():
            return self.__default_sass_command()

        node_modules_exe = f"{node_modules_exe}"
        result = subprocess.run(
            [node_modules_exe, "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return self.__default_sass_command()

        self.stdout.write(f"Using {node_modules_exe}")
        return node_modules_exe

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
        result = subprocess.run(
            [self.sass_command, "--version"], capture_output=True, text=True
        )
        result.check_returncode()
        sass_version = result.stdout.strip()
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
            f"{self.sass_command} {action} --style compressed {folders} "
            "--load-path aidants_connect_common/static/scss/"
        )
        self.stdout.write(f"Running {command}")
        self.write_horizontal_line()
        os.system(command)

    def write_horizontal_line(self):
        self.stdout.write("-" * 15)

    def __default_sass_command(self):
        found = which("sass")
        if found is None:
            raise CommandError(
                "You need to install sass before using this command.\n"
                "Use either NPM or check https://sass-lang.com/install"
            )

        self.stdout.write(f"Using {found}")
        return found
