def flatten_list(nested_list: list[list]) -> list:
    return [item for sublist in nested_list for item in sublist]


def unpack_bolt_data(bolt_data: list[dict]) -> tuple[dict, dict]:
    """Unpacks bolt data into a tuple of (facts, packages)"""
    facts = [x for x in bolt_data if "facts" in x][0]["facts"]
    packages = [x for x in bolt_data if "packages" in x][0]["packages"]
    return facts, packages


def partial_match(lst: list[str], q: str) -> bool:
    return any(q in s for s in lst)
