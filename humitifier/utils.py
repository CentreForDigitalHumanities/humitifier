def flatten_list(nested_list: list[list]) -> list:
    return [item for sublist in nested_list for item in sublist]


def partial_match(lst: list[str], q: str) -> bool:
    return any(q in s for s in lst)
