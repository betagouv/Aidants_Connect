NO_VALUE = object()


def strtobool(val, default=NO_VALUE):
    val = str(val).lower()
    truthy = ("y", "yes", "t", "true", "on", "1")
    falsy = ("n", "no", "f", "false", "off", "0")
    if val in truthy:
        return True
    elif val in falsy:
        return False
    elif default is not NO_VALUE:
        return default
    else:
        raise ValueError(
            "Invalid boolean value %r, authorized values are %r and %r"
            % (val, truthy, falsy)
        )
