## Humitifier

A CMDB + interface for tracking the inventory servers.
Based on the infrastructure of Humanities IT within the UU, but probably applicable to other infrastructures too. 

Broadly speaking there are 3 parts to humitifier:

* Backend
  * Server fact collection over SSH
  * stdout parsing of bash command outputs
* Frontend
  * A CSS style sheet mimicing the UU vibe
  * HTMX for hot-reloading parts of a page with plain HTML
* Dev-backend
  * Faking module for all used data structures

The intended way to use this is to keep a private repository of `.toml` files of servers that you wish to monitor.
These will be refered to as `service contracts` and not only are they the entry point for connecting to a server over ssh, they also function as a way to store additional metadata, such as the lifetime of a server and the contect details of the people who make use of it.

### Is it for me?

A humitifier user has the following properties:

* maintains a bunch of on-prem servers
* doesn't need fancy graphs and metrics, just facts and numbers and maybe some red exclamation marks
* doesn't care about historic data, just wants to know if something is up right now
* wants to track not just server data, but also if it is time to retire a server and who to contact in that case

### Fundamental technology choices
At present, there are 5 core technologies that server as the backbone for the application.
Below is a motivation of why they were chosen:

* **fastapi** is used as a webserver. It is light-weight, modern, well-maintained, and well-documented. Additionally it comes with support for strong type declarations through `pydantic` which ensures fewer mistakes in development. It makes use of `flask`-like url decoration making it relatively easy to understand. Finally, it is designed with async compatibility, which is not really very relevant, but very cutting-edge and therefore cool. 
  * A consideration was to use django because it is the framework that is used most in our department, but then a decision was made to not get stuck in old ways
* **jinja2** is used for templating. It is the most-used python library for serving dynamic html content. It is likely the format that most people are familiar with in python web development as it is the templating engine for django.
  * To facilitate further development the most prevalent engine was chosen
* **htmx** is used for hot-reloading frontend content. `htmx` allows for having a greatly simplified dynamic fronted experience as alll state is managed on the backend. As bonus, you do not have to download the internet through npm to have it work. 
  * most traditional frontend frameworks require a lot of javascript overhead, due to the scope of the project the choice is made to not include this layer of complexity
* **parallel-ssh** is used to run remote ssh commands
  * `asyncssh` was a nice contender, however it had an incompatible license
  * `pyinfra` did not really offer much more than pre-implemented ssh commands and was using a considerably slower library for running the ssh commands
* **toml** is used for maintaining infrastructure in code. It is (subjectively) easier to read than `yaml`

### Open design questions

* [ ] to database or not to database:
  * The collection of facts is pretty quick; you could just run a cron job to restart the app an re-colelct facts every 15 minutes
  * Working with a database includes overhead (orm, db connection)
  * Is historic data really relevant for day-to-day monitoring?
* [ ] how do the service contracts work?
  * what's mandatory and what's optional?
  * can you configure server clusters through toml files?
  * how should you organize your service contracts?
* [ ] how to run a production version?
  * docker or no? 
  * as a constant server or as a mini-service that constantly restarts?
* [ ] What things should be instantly visible?
  * When is something a "critical" issue?

### Future plans

- [ ] Health checks on web-applications
- [ ] Security advisories on server packages
- [ ] Security advisories on application packages


## Development Setup
To run the project locally you must install all relevant dependencies in a venv.

```bash
python3 -m venv .venv
poetry install
```

* To run tests you can run `pytest`.
* To run a local development server, you can run `make dev-server`
* The dev server uses fake data and requires no additional configuration. 

## Production setup
*In progress of figuring out...*
