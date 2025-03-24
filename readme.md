# Humitifier

A CMDB + interface for tracking the inventory servers.
Based on the infrastructure of Humanities IT within the UU, but probably applicable to other infrastructures too.

Humitifer is split into two-ish components

* Scanner
  * Server artefact collection over SSH
  * stdout parsing of bash command outputs
* Server
  * Processing scan output
  * A frontend interface for displaying scan results
* Common
  * A shared library for both components, containing mostly data-model code

## Is it for me?

A humitifier user has the following properties:

* maintains a bunch of on-prem servers
* doesn't need fancy graphs and metrics, just facts and numbers and maybe some red exclamation marks
* wants to track not just server data, but also if it is time to retire a server and who to contact in that case


## Fundamental technology choices

At present, there are 4 core technologies that server as the backbone for the application.
Below is a motivation of why they were chosen:

* **Django** is used as a webserver. It is light-weight, modern, well-maintained, and well-documented. In addition, there is a lot of institutional knowledge about it in the department.
  * Versions <3.0 used FastAPI, but as new requirements came in, it was decided to switch to Django to facilitate faster development
  * The UI uses TailwindCSS for styling and AlpineJS for interactivity. Tailwind was chosen mostly because the developer didn't want to use UU-Bootstrap. AlpineJS was chosen because it is very modern alternative to jQuery, perfect for the minimal interactivity needed in the app.
* **paramiko** is used to run remote ssh commands
  * Previous versions <4.0 used parallel-ssh, which is a parallel-running optimized libray. Humitifier 4 introduces a different strategy, making paramiko the better fit
* **Celery** is used to schedule scans/processing/background jobs. The scanner can run as a dedicated scan-worker or a standalone app
* **Pydantic** is used to describe internal data-models. Chosen for it's advanced serialization and Celery support
  * The scanner also uses pydantic-settings for the configuration/cli interface

# Setup

## Additional components

Humitifier requires a PostgreSQL database and a RabbitMQ instance to run.

You can use the following docker-compose file to set these up:

```yaml
services:
  server-db:
    image: postgres:15
    expose:
      - "5432"
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
  rabbitmq:
    image: rabbitmq:4-management
    expose:
      - "5672"
    ports:
      - "15672:15672"
      - "5672:5672"
    environment:
        RABBITMQ_DEFAULT_USER: humitifier
        RABBITMQ_DEFAULT_PASS: humitifier
```

## Server configuration
The server ships with sensible development configuration by default.
However, it can be configured using environment variables if needed.

### Development setup

To run the project locally you must use `poetry` to install the dependencies.
This will create a virtual environment and install the dependencies in it.

```bash
poetry install
```

To run a local development server, you can run `python src/manage.py runserver`

You will also need to run a Celery worker and scheduler using the
server-codebase. In production, these should be separate. For development,
you can run a combined worker-scheduler:
`pythom -m celery -A humitifier_server worker -Q default -l INFO --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`


## Agent configuration
The app configuration is written in `toml`. (Or env vars, if you want)
In it you specify ssh configuration, inventory/database values, and task interval values.
An example config:

```toml
[ssh]
user = "<user>"
private_key = "<private key>"
#private_key_password = "<pkey password>" # optional

[ssh.bastion] # Optional, can be left out for direct connections
host = "<bastion server>"
user = "<user>"
private_key = "<private key>"
#private_key_password = "<pkey password>" # optional

[celery]
rabbit_mq_url = "amqp://<user>:<pass>@localhost//"

```
Place this file in `humitifier-scanner/.local/config.toml`

### Development Setup

To run the project locally you must use `poetry` to install the dependencies.
This will create a virtual environment and install the dependencies in it.

```bash
poetry install
```

Either run the scanner manually using `cli.py` (`./cli.py -h` for usage).
Or run

### Production setup

The suggested production setup uses `docker-compose`.
Refer to the example file for a configuration.


