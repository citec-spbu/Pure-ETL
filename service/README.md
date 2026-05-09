# Information extraction service

Tools used:

- just: [just](https://github.com/casey/just)
- uv: [uv](https://docs.astral.sh/uv/)
- podman: [podman](https://podman.io)

Suggested also:

- dbeaver: [dbeaver.io](https://dbeaver.io)

## Почему podman а не docker

Для него не нужен root - он работает полностью в user space.

## Postgres database

Postgres бд используется для хранения трансформированных данных.

ETL сервис и Dash приложение независимо подключаются к postgres.

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

REST сервис используется для ETL.

To start the service (if you don't have the postgres image, use `just pg-pull` to pull it):

```sh
just pg-up pg-wait pg-migrate
just serve
```

### Use the API

API можно попробовать на http://localhost:8000/schema (Rapidoc as default).
Там же можно почитать и документацию на ручки.

Or go to http://localhost:8000/schema/swagger if you like Swagger more.

### Load data

Загрузить все доступные json данные можно следующей командой:

```sh
just load-all-suggested
```

## Dash app

Dash app is used for analysis.
It is a multipage app - look for navigation at the top of the page.

```sh
just dash
```

> [!NOTE]
> Dash app needs the database

As of now, dash app does not need the REST service.

## Documentation

Чтобы понять что происходит, можно начать с внимательного изучения `./justfile`.

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
    - [x] persons
    - [x] organisational-units
    - [x] classification-schemes
    - [x] research-outputs stub
    - [x] research-outputs links
    - [ ] persons-units links data
    - [ ] research-outputs
    - [ ] ...
- [x] Reload loaded Pure data
- [ ] Improve logging configuration
- [ ] Test database performance on real-life size dataset and add indexes where appropriate
