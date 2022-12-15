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
