# Humitifier

A CMDB + interface for tracking the inventory servers.
Based on the infrastructure of Humanities IT within the UU, but probably applicable to other infrastructures too.

Humitifer is split into two components

* Agent
  * Server fact collection over SSH
  * stdout parsing of bash command outputs
* Server
  * A frontend interface for displaying scan results

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
* **parallel-ssh** is used to run remote ssh commands
  * It is no longer maintained, and thus Humitifier will probably switch to a different library in Humitifier 4.0
  * `asyncssh` was a nice contender, ~~however it had an incompatible license~~ no idea what that license problem was, it's explicitly allowed....
  * `pyinfra` did not really offer much more than pre-implemented ssh commands and was using a considerably slower library for running the ssh commands
* **rocketry** is used by the agent to schedule scans. Again, it is no longer maintained, and will probably be replaced in Humitifier 4.0.
* **toml** is used for configuration of the agent. It's better than JSON, and built-in to Python. 


# Setup

## Server configuration

The default settings of the server application are already correct for local development. You will need to provide
it with a postgresql database listening on `localhost:6432` with a database named `postgres` and a user `postgres`
with password `postgres`. Do note that this is a non-standard port for postgresql! (The agent was already using 5432...)

You can use the following docker-compose file to set up the database:

```yaml
services:
  server-db:
    image: postgres:15
    ports:
      - "6432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
```

### Development setup

To run the project locally you must use `poetry` to install the dependencies.
This will create a virtual environment and install the dependencies in it.

```bash
poetry install
```

To run a local development server, you can run `python src/manage.py runserver` 

## Agent configuration
The app configuration is written in `toml`.
In it you specify ssh configuration, inventory/database values, and task interval values.
An example config:

```toml
db = "postgresql:/..."
upload_endpoint = "https://example.com/api/upload_scans/" # The endpoint (of the server-app) to upload scans to
inventory = ["example.com"] # Not actually used anymore. Still required tho!

[pssh] # any pssh configuration to access your servers
user = "don"
timeout = 15
num_retries = 0
pool_size = 50

[tasks]
infra_update = "every 15 minutes"
```
To use this config, set the environment varaible `HUMITIFIER_CONFIG` (e.g. `HUMITIFIER_CONFIG=local.toml python entrypoint/main.py`)

### Host configuration
Host configurations are defined in the app config under the inventory key. 
This is ignored, and you should fill the `hosts` table in the database manually.


### Development Setup

To run the project locally you must use `poetry` to install the dependencies.
This will create a virtual environment and install the dependencies in it.

```bash
poetry install
```

To run a local development server, you can run `python entrypoint/local.py` 
If not specified, the app will look for a file `.local/app_config.toml` as its configuration file.
To override this, specify a `HUMITIFER_CONFIG` env var.

### Production setup

The suggested production setup uses `docker-compose`.
Refer to the example file for a configuration.


