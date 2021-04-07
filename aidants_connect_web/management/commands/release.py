import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new tag using provided version number"

    def handle(self, *args, **options):
        self.stdout.write("Here are the latest versions:")
        os.system("git tag -l | tail")
        version = input("Which version number will you give to the new version? ")
        are_they_sure = input(
            self.style.WARNING(f"Version {version}, are you sure? (y/N) ")
        )
        if are_they_sure.lower().strip() != "y":
            self.stdout.write(
                "You’re right, there’s no rush. Try again when you are ready."
            )
            return
        self.stdout.write("OK, let’s tag this then!")

        os.system(f'git tag -a {version} -m ""')
        os.system("git push --tags")

        self.stdout.write(
            self.style.SUCCESS(f"Tag {version} was pushed to git origin!")
        )
