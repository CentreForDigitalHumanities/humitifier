# Dockerfile
FROM ghcr.io/centrefordigitalhumanities/build-containers/ubuntu2004-py3.13-pyinstaller:main
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory for the build process
WORKDIR /app

COPY humitifier-scanner/pyproject.toml humitifier-scanner/poetry.lock .
# Needed for poetry....
COPY humitifier-scanner/README.md ./
COPY humitifier-scanner/src/ ./src

RUN mkdir /humitifier-common
COPY humitifier-common/* /humitifier-common/

# Install depedencies
RUN poetry install --only=main,standalone,dev --compile --no-interaction -vvv

# Build the binary using PyInstaller
RUN poetry run -- pyinstaller -F --clean -n humitifier-scanner src/cli.py
