## Humitifier

A CMDB + interface for tracking the inventory servers.
Based on the infrastructure of Humanities IT within the UU, but probably applicable to other infrastructures too. 

## Development Setup
To run the project locally you must install all relevant dependencies in a venv.

```bash
python3 -m venv .venv
poetry install
```

* To run tests you can run `pytest`.
* To run a local development server, you can run `make dev-server`
* The dev server uses fake data and requires no additional configuration. 

