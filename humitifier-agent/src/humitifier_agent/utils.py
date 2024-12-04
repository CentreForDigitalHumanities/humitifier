def os_in_list(os: str, os_list: list[str]) -> bool:
    os_lwr = os.lower()

    return any(os_item in os_lwr for os_item in os_list)
