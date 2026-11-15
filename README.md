# Overtime

A small, single-user web app for recording and reviewing overtime. Log time by date, edit or delete entries, see totals by month and overall, and export your entries as CSV.

The app is built with Flask and SQLite and runs in Docker on port `8000`.

## Features

- Password-protected access for one user
- Log time as hours, minutes, or both; decimal hours and long minute values are supported
- Review, edit, and delete entries, with monthly and overall totals
- Export entries as CSV
- Persistent SQLite storage and a `/healthz` health check

## Quick start with Docker

Build the image and start the app with a persistent Docker volume:

```sh
docker build -t overtime .
docker run --rm -p 8000:8000 \
  -e COOKIE_SECURE=false \
  -e SECRET_KEY=dev \
  -e APP_USERNAME=me \
  -e APP_PASSWORD=test \
  -v overtime-data:/data \
  overtime
```

Open [http://localhost:8000](http://localhost:8000). This example is for local testing only: use a strong secret and password, and keep secure cookies enabled when serving the app over HTTPS.

## Configuration

The app requires a secret key, username, and either a password hash or a plain-text password. A password hash is recommended.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Flask session signing key. Use a long, random value. Changing it invalidates existing sessions. |
| `APP_USERNAME` | Yes | — | The single login username. |
| `APP_PASSWORD_HASH` | One of these is required | — | Werkzeug password hash. Takes precedence if both password settings are set. |
| `APP_PASSWORD` | One of these is required | — | Plain-text password fallback; use a hash when possible. |
| `COOKIE_SECURE` | No | `true` | Set to `false` only for local testing over HTTP. Keep the default when using HTTPS. |
| `DB_PATH` | No | `/data/overtime.db` | SQLite database file path. |

Generate a secret key with:

```sh
openssl rand -hex 32
```

Generate a password hash with Docker:

```sh
docker run --rm -it python:3.12-slim sh -c "pip install -q werkzeug && python -c 'import getpass; from werkzeug.security import generate_password_hash as g; print(g(getpass.getpass()))'"
```

If you put the hash in a `.env` file, enclose it in single quotes because it contains `$` characters. If your deployment tooling mangles the hash, `APP_PASSWORD` is supported as an alternative.

## Docker Compose

Copy `.env.example` to `.env` and set `SECRET_KEY`, `APP_USERNAME`, and `APP_PASSWORD_HASH`. Then start the service:

```sh
docker compose up --build -d
```

Compose keeps the database in the `overtime-data` named volume. The supplied Compose file does not publish port `8000` to the host; connect it to your reverse proxy or adjust the Compose port configuration if you need direct host access. When exposed publicly, use HTTPS and leave `COOKIE_SECURE` enabled.

## Data and backups

The SQLite database is stored at `/data/overtime.db` inside the container (in the Docker volume when using the examples above). Stop the app before copying the database file for a backup.

## Container image

The published image is `ghcr.io/erikpersson0884/overtime/app:latest`. The GitHub Actions workflow builds and publishes `linux/amd64` and `linux/arm64` images when changes are pushed to `main`.

The container listens on port `8000` and includes a health check at `/healthz`.

# Authors

<p align="center">
  <img src="https://github.com/erikpersson0884.png?size=100" alt="Erik Persson" width="100" height="100" />
  <br />
  <strong><a href="https://github.com/erikpersson0884">Erik Persson</a></strong><br />
  Creator &amp; Maintainer
</p>