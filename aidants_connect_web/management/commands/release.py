import os

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generate a new tag using provided version number"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only display changelog, do not tag-push anything",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if not dry_run:
            self.check_current_branch()
            self.version = self.ask_for_new_version()

            if not self.confirm_if_ok():
                self.stdout.write(
                    "You’re right, there’s no rush. Try again when you are ready."
                )
                return
            self.stdout.write("OK, let’s release aidants-connect, then!")

        self.changelog = self.display_and_get_changelog()

        if not dry_run:
            self.tag_and_push_on_origin(self.version, self.changelog)

    def check_current_branch(self):
        current_branch = os.popen("git rev-parse --abbrev-ref HEAD")
        if current_branch != "main":
            raise CommandError(
                "This script is intended to work ONLY on branch 'main'.\n"
                "You can use it with the option --dry-run on any branch, though."
            )

    def ask_for_new_version(self):
        self.stdout.write("Here are the latest versions:")
        os.system("git tag -l | tail -5")
        version = input("How will you name this new version? ")
        return version

    def confirm_if_ok(self):
        are_they_sure = input(
            self.style.WARNING(f"Version {self.version}, are you sure? (y/N) ")
        )
        return are_they_sure.lower().strip() == "y"

    def display_and_get_changelog(self):
        previous_version = os.popen("git tag | tail -1").read().strip()
        command = (
            f"git log --pretty='format:%s' --first-parent main {previous_version}..main"
        )
        changelog = os.popen(command).read()
        self.stdout.write(
            f"\nHere is the changelog since {previous_version},"
            "you may want to use it for production log:"
        )
        self.write_horizontal_line()
        self.stdout.write(changelog)
        self.write_horizontal_line()
        return changelog

    def tag_and_push_on_origin(self, version, message):
        cleaned_message = message.replace("'", "’")
        os.system(f"git tag -a {version} -m '{cleaned_message}'")
        os.system("git push --tags")
        self.stdout.write(
            self.style.SUCCESS(f"Tag {version} was pushed to git origin!")
        )

    def write_horizontal_line(self):
        self.stdout.write("-" * 15)
