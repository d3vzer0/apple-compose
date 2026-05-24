# apple-compose

`apple-compose` is a Docker compose-like CLI for Apple Containers. It reads a compose yaml file, builds an execution
plan and translates that plan into Apple `container` CLI commands. The project is intentionally thin, the Apple
`container` CLI remains responsible for runtime behavior.

## Requirements

- Python 3.14+
- `uv` for development
- Apple `container` CLI installed and available on `PATH`

## Install

```bash
uv tool install .
```

## Usage

Global options follow Docker Compose-style syntax:

```bash
apple-compose -f compose.yaml up -d
apple-compose --dry-run -f compose.yaml up --build_
```

If `--file/-f` is not provided, `apple-compose` defaults to `docker-compose.yml`.

See [docs/commands.md](docs/commands.md) for the generated command reference.

## Tests

Run the default test suite with a dummy container CLI:

```bash
uv run pytest tests
```

Live end-to-end tests that use the real Apple `container` CLI:

```bash
uv run pytest tests --live-tests
```

The live tests use `alpine:latest` by default. Override the image with `APPLE_COMPOSE_E2E_IMAGE`:

```bash
APPLE_COMPOSE_E2E_IMAGE=alpine:latest uv run pytest tests --live-tests
```
