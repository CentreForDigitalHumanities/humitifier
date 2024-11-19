import re
from io import BytesIO

import tomli
import tomli_w
import argparse

PYPROJECT_FILES = [
    "humitifier-server/pyproject.toml",
    "agent/pyproject.toml",
]
PYTHON_FILES = [
    "humitifier-server/src/humitifier_server/settings.py",
]


def bump_version(file_path, new_version=None):
    # Read the pyproject.toml file
    with open(file_path, "rb") as file:
        pyproject_content = tomli.load(file)

    pyproject_content["tool"]["poetry"]["version"] = new_version

    buffer = BytesIO()
    tomli_w.dump(pyproject_content, buffer)

    with open(file_path, "wb") as file:
        tomli_w.dump(pyproject_content, file)


def update_version_in_spectacular_settings(file_path, new_version):
    # Yes, this is terrible. But it works.

    with open(file_path, "r") as file:
        lines = file.readlines()

    pattern = re.compile(r'(\s*"VERSION"\s*:\s*")(\d+\.\d+\.\d+)(".*)')
    updated_lines = []

    for line in lines:
        match = pattern.match(line)
        if match:
            updated_line = f"{match.group(1)}{new_version}{match.group(3)}\n"
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    with open(file_path, "w") as file:
        file.writelines(updated_lines)


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Bump version")
    argparser.add_argument("new_version", type=str, help="New version")
    args = argparser.parse_args()

    for file in PYPROJECT_FILES:
        bump_version(file, args.new_version)

    for file in PYTHON_FILES:
        update_version_in_spectacular_settings(file, args.new_version)
