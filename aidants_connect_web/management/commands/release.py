import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new tag using provided version number"

    def handle(self, *args, **options):
        self.version = self.ask_for_new_version()

        if not self.confirm_if_ok():
            self.stdout.write(
                "You’re right, there’s no rush. Try again when you are ready."
            )
            return
        self.stdout.write("OK, let’s tag this then!")

        self.tag_and_push_on_origin(self.version)

    def ask_for_new_version(self):
        self.stdout.write("Here are the latest versions:")
        os.system("git tag -l | tail")
        version = input("Which version number will you give to the new version? ")
        return version

    def confirm_if_ok(self):
        are_they_sure = input(
            self.style.WARNING(f"Version {self.version}, are you sure? (y/N) ")
        )
        return are_they_sure.lower().strip() == "y"

    def tag_and_push_on_origin(self, version):
        os.system(f'git tag -a {version} -m ""')
        os.system("git push --tags")
        self.stdout.write(
            self.style.SUCCESS(f"Tag {version} was pushed to git origin!")
        )
