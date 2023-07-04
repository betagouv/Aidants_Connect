from django.conf import settings


def join_url_parts(base: str, *args):
    if len(args) == 0:
        return base
    head, tail = args[:-1], args[-1]
    parts = "/".join(
        [
            *[arg.removeprefix("/").removesuffix("/") for arg in head],
            tail.removeprefix("/"),
        ]
    )
    return f"{base.removesuffix('/')}/{parts}"


def build_url(path: None):
    path = path or ""
    return (
        f"http{'s' if settings.SSL else ''}://{settings.HOST.removesuffix('/')}"
        f"/{path.removeprefix('/')}"
    )
