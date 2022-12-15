from json import dumps, loads
from pathlib import Path


def load_json_fixture(name: str, as_string=False) -> dict:
    path = Path(__file__).parent / "fixtures" / name
    with open(path) as f:
        result = loads(f.read())
        return dumps(result) if as_string else result
