# Humitifier

A CMDB + interface for tracking the inventory servers.
Based on the infrastructure of Humanities IT within the UU, but probably applicable to other infrastructures too.

Broadly speaking there are 3 parts to humitifier:

* Backend
  * Server fact collection over SSH
  * stdout parsing of bash command outputs
* Frontend
  * A CSS style sheet mimicing the UU vibe


The intended way to use this is to keep a private repository of `.toml` files of servers that you wish to monitor.
These will be refered to as `service contracts` and not only are they the entry point for connecting to a server over ssh, they also function as a way to store additional metadata, such as the lifetime of a server and the contect details of the people who make use of it.

## Is it for me?

A humitifier user has the following properties:

* maintains a bunch of on-prem servers
* doesn't need fancy graphs and metrics, just facts and numbers and maybe some red exclamation marks
* doesn't care about historic data, just wants to know if something is up right now
* wants to track not just server data, but also if it is time to retire a server and who to contact in that case



## Fundamental technology choices

At present, there are 4 core technologies that server as the backbone for the application.
Below is a motivation of why they were chosen:

* **fastapi** is used as a webserver. It is light-weight, modern, well-maintained, and well-documented. Additionally it comes with support for strong type declarations through `pydantic` which ensures fewer mistakes in development. It makes use of `flask`-like url decoration making it relatively easy to understand. Finally, it is designed with async compatibility, which is not really very relevant, but very cutting-edge and therefore cool.
  * A consideration was to use django because it is the framework that is used most in our department, but then a decision was made to not get stuck in old ways
* **jinja2** is used for templating. It is the most-used python library for serving dynamic html content. It is likely the format that most people are familiar with in python web development as it is the templating engine for django.
  * To facilitate further development the most prevalent engine was chosen
* **parallel-ssh** is used to run remote ssh commands
  * `asyncssh` was a nice contender, however it had an incompatible license
  * `pyinfra` did not really offer much more than pre-implemented ssh commands and was using a considerably slower library for running the ssh commands
* **toml** is used for maintaining infrastructure in code. It is (subjectively) easier to read than `yaml`


# Setup

## App configuration
The app configuration is written in `toml`.
In it you specify ssh configuration, inventory/database values, and task interval values.
An example config:

```toml
db = "/data/facts.db"
inventory = "/data/inventory" # A directory with toml files with host configurations

[pssh] # any pssh configuration to access your servers
user = "don"
timeout = 15
num_retries = 0
pool_size = 50

[tasks]
infra_update = "every 15 minutes"
```
To use this config, set the environment varaible `HUMITIFIER_CONFIG` (e.g. `HUMITIFIER_CONFIG=local.toml python entrypoint/main.py`)

## Host configuration
Host configurations are defined in `toml` as such:

```toml
["gw-c-10yup.im.hum.uu.nl"]
department = "Humanities"
contact.name = "Don"
contact.email = "blah@uu.nl"

# any other metadata
```

## Development Setup

To run the project locally you must install all relevant dependencies in a venv.

```bash
python3 -m venv .venv
poetry install
```

To run a local development server, you can run `python entrypoint/local.py` 
If not specified, the app will look for a file `.local/app_config.toml` as its configuration file.
To override this, specify a `HUMITIFER_CONFIG` env var.

## Production setup

The suggested production setup uses `docker-compose`.
Refer to the example file for a configuration.

### Running without `docker-compose`

Since `humitifier` uses `sqlite` and no other services, you can also run it with docker.
An example command: 

```bash
docker run -d -p 8000:8000 \
  -e SSH_AUTH_SOCK=/ssh-agent \
  -e HUMITIFIER_CONFIG=/code/app_config.toml \
  -v $(pwd)/app_config.toml:/code/app_config.toml \
  -v $(pwd)/data:/data \
  -v $SSH_AUTH_SOCK:/ssh-agent \
  ghcr.io/centrefordigitalhumanities/humitifier/humitifier:latest
```

