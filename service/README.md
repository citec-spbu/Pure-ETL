# Information extraction service

Tools used:

- just: [just](https://github.com/casey/just)
- uv: [uv](https://docs.astral.sh/uv/)
- podman: [podman](https://podman.io)

## Postgres database

Postgres database is used to store transformed data.

If you don't have the postgres image, use `just pg-pull` to pull it.

```sh
just pg-up pg-wait pg-migrate
```

## Tests

Try and run tests:

```sh
just test
```

> [!IMPORTANT]
> Tests need a fresh database.
> Use the following command if you need a clean one.

```sh
just pg-down pg-up pg-wait pg-migrate
```

## Jupyter Notebook

To start jupyter lab

```sh
just jupyter
```

Open `./experiment.ipynb`

## REST service

REST service is used for ETL.

To start the service (if you don't have the postgres image, use `just pg-pull` to pull it):

```sh
just pg-up pg-wait pg-migrate
just serve
```

### Use the API

Try API at [http://localhost:8000/schema]

### Load data

Load all available persons with

```sh
just load-all-persons
```

## Dash app

Dash app is used for analysis.

> [!Note]
> Dash app needs the database

```sh
just dash
```

As of now, dash app does not need the rest service.

## Documentation

To figure out what is happening, start with exploring `./justfile`

## To do:

- [x] Add configuration
- [x] Add Postgres database
- [x] Add testing framework
- [x] Add Litestar
- [x] Add openapi
- [x] Add logging
- [x] Setup alembic migrations
- [x] Add UI solution (Streamlit/Dash-Plotly/NiceGUI/Reflex/Shiny)
- [ ]  Use async (maybe?)
- [ ] Add auth (Authelia?)
- [ ] Add metrics
- [ ] Add transform + load for all objects
    - [x] persons example
    - [ ] persons
    - [ ] ...
- [ ] Improve logging configuration
