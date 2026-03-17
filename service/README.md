# Information extraction service

Tools used:

- just: [https://github.com/casey/just]
- uv: [https://docs.astral.sh/uv/]
- podman: [https://podman.io]

## Jupyter Notebook

To start jupyter lab

```sh
just jupyter
```

Open `./experiment.ipynb`

## REST service

To start the service (if you don't have the postgres image, use `just pg-pull` to pull it):

```sh
just pg-up
just serve
```

Try and run tests:

```sh
just test
```

> [!IMPORTANT]
> Tests need a fresh database.
> Use the following command to get a clean one.

```sh
just pg-down && just pg-up
```

Try API at [http://localhost:8000/schema]

## Documentation

To figure out what is happening, start with exploring `./justfile`

## To do:

- [x] Add configuration
- [x] Add Postgres database
- [x] Add testing framework
- [x] Add Litestar
- [x] Add openapi
- [x] Add logging
- [ ] Use async
- [ ] Setup alembic migrations
- [ ] Add UI solution (Streamlit/Dash-Plotly/NiceGUI/Reflex/Shiny)
- [ ] Add auth (Authelia?)
- [ ] Add metrics
- [ ] Add transform + load for all objects
    - [x] persons example
    - [ ] persons
    - [ ] ...
- [ ] Improve logging configuration
