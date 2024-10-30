from os import environ

get = environ.get

def get_boolean(key: str, default) -> bool:
    return get(key, default=str(default)).lower() in ("true", "1", "yes", 't')