from django.conf import settings


def join_url_parts(base: str, *args):
    if len(args) == 0:
        return base
    rest, tail = args[:-1], args[-1]
    parts = "/".join(
        [
            *[arg.removeprefix("/").removesuffix("/") for arg in rest],
            tail.removeprefix("/"),
        ]
    )
    return f"{base.removesuffix('/')}/{parts}"


def build_url(path: None | str):
    path = path or ""
    return (
        f"http{'s' if settings.SSL else ''}://{settings.HOST.removesuffix('/')}"
        f"/{path.removeprefix('/')}"
    )
