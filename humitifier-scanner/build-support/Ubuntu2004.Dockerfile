# Dockerfile
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies required for building Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    libbz2-dev \
    libsqlite3-dev \
    zlib1g-dev \
    libssl-dev \
    libffi-dev \
    libreadline-dev \
    libncurses5-dev \
    libgdbm-dev \
    liblzma-dev \
    uuid-dev \
    xz-utils \
    tk-dev

# Download and Build Python 3.13
RUN wget https://www.python.org/ftp/python/3.13.2/Python-3.13.2.tar.xz --no-check-certificate && \
    tar -xf Python-3.13.2.tar.xz && \
    cd Python-3.13.2 && \
    ./configure --enable-optimizations --enable-shared && \
    make -j$(nproc) && \
    make altinstall
RUN ldconfig -v

# Set Python 3.13 as the default Python
RUN ln -sf /usr/local/bin/python3.13 /usr/bin/python && \
    ln -sf /usr/local/bin/pip3.13 /usr/bin/pip

# Install poetry
RUN pip install poetry && poetry config virtualenvs.in-project true

# Set the working directory for the build process
WORKDIR /app

# Copy the source code of your Python application
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
