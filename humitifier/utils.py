def flatten_list(nested_list: list[list]) -> list:
    return [item for sublist in nested_list for item in sublist]
