import os
from pathlib import Path


def add_lowercase_env_vars(prefix: str) -> None:
    """pydantic_settings expects lowercase env vars; as env vars are usually
    uppercase, this is annoying.

    This function adds a lowercase version of each env var that starts with the
    prefix, allowing us to use uppercase env vars.
    :param prefix:
    :return:
    """
    for env_var, value in os.environ.items():
        if env_var.startswith(prefix):
            os.environ[env_var.lower()] = value


def generate_config_locations(base_dir: Path, app_name: str, env_var: str) -> list[Path]:
    locations = [
        base_dir / Path("../../.local/config.toml"),
        (Path("~/.config/humitifier/") / app_name / "config.toml").expanduser(),
        (Path("~/.humitifier/") / app_name / "config.toml").expanduser(),
        Path("/etc/humitifier/") / app_name / "config.toml",
        Path("/usr/local/etc/humitifier/") / app_name / "config.toml",
    ]
    if config_in_env := os.environ.get(env_var):
        locations.insert(0, Path(config_in_env))

    return locations
