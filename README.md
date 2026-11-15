# Overtime

A small, single-user web app for recording and reviewing overtime. Log time by date, edit or delete entries, review monthly and overall totals, and export your entries as CSV.

[![Last Commit][last-commit-shield]][last-commit-url]
[![Build Status][build-shield]][build-url]
[![Repo Size][repo-size-shield]][repo-size-url]
[![Author][author-shield]][author-url]

## Index

1. [About the project](#about-the-project)
2. [Features](#features)
3. [Built with](#built-with)
4. [Getting started](#getting-started)
5. [Configuration](#configuration)
6. [Scripts](#scripts)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Contributing](#contributing)
11. [Authors](#authors)

# About the project

Overtime is a small Flask application for keeping track of personal overtime. It stores entries in SQLite and provides a simple web interface to log and manage time, view totals, and download a CSV export.

## Features

- Password-protected access for one user
- Log time by date using hours, minutes, or both; decimal hours and long minute values are supported
- View entries grouped by month, with monthly and overall totals
- Edit or delete entries
- Export logged time as CSV
- Persistent SQLite storage and a `/healthz` health check

## Built with

[![Python][tech-1-shield]][tech-1-url]
[![Flask][tech-2-shield]][tech-2-url]
[![SQLite][tech-3-shield]][tech-3-url]

# Getting started

## Prerequisites

- Docker
- Docker Compose (for the Compose deployment)

## Installation

Clone the repository and prepare the environment file:

```sh
git clone https://github.com/erikpersson0884/overtime.git
cd overtime
cp .env.example .env
```

Set `SECRET_KEY`, `APP_USERNAME`, and `APP_PASSWORD_HASH` in `.env`, then build and run the app locally:

```sh
docker build -t overtime .
docker run --rm -p 8000:8000 \
  --env-file .env \
  -e COOKIE_SECURE=false \
  -v overtime-data:/data \
  overtime
```

Open [http://localhost:8000](http://localhost:8000). `COOKIE_SECURE=false` is for local HTTP testing only. Keep secure cookies enabled when serving the app over HTTPS.

# Configuration

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

The hash contains `$` characters. If you put it in a `.env` file, enclose it in single quotes. If your deployment tooling mangles the hash, `APP_PASSWORD` is supported as an alternative.

# Scripts

| Command | What it does |
|---|---|
| `docker build -t overtime .` | Build the Docker image locally. |
| `docker run --rm -p 8000:8000 ...` | Run the app locally on port `8000`. |
| `docker compose up --build -d` | Build and start the Compose service. |
| `docker compose down` | Stop the Compose service; the named data volume is retained. |

# Testing

There is no automated test suite in the repository. For a basic runtime check, start the app and visit `http://localhost:8000/healthz`; it should return `ok`.

# Deployment

The repository includes a `Dockerfile` and a `docker-compose.yml`. Configure `.env` with `SECRET_KEY`, `APP_USERNAME`, and `APP_PASSWORD_HASH`, then start the Compose service:

```sh
docker compose up --build -d
```

The Compose file does not publish port `8000` to the host. Connect the service to your reverse proxy or adjust the Compose port configuration if you need direct host access. Use HTTPS for public access and leave `COOKIE_SECURE` enabled.

The published image is `ghcr.io/erikpersson0884/overtime/app:latest`. The GitHub Actions workflow publishes `linux/amd64` and `linux/arm64` images when changes are pushed to `main`.

**Runtime details:**

- **Port:** The container listens on port `8000`.
- **Health check:** `GET /healthz` returns `ok`.
- **Data:** SQLite is stored at `/data/overtime.db` in the persistent `overtime-data` volume. Stop the app before copying the database file for a backup.

# Contributing

1. Fork the repository.
2. Create a branch (`git checkout -b feature-branch`).
3. Make your changes and build the Docker image to check them.
4. Commit and push your branch.
5. Open a pull request.


# Authors

<p align="center">
  <img src="https://github.com/erikpersson0884.png?size=100" alt="Erik Persson" width="100" height="100" />
  <br />
  <strong><a href="https://github.com/erikpersson0884">Erik Persson</a></strong><br />
  Creator &amp; Maintainer
</p>


[last-commit-shield]: https://img.shields.io/github/last-commit/erikpersson0884/overtime/main?style=for-the-badge&cacheSeconds=30
[last-commit-url]: https://github.com/erikpersson0884/overtime/commits/main

[repo-size-shield]: https://img.shields.io/github/repo-size/erikpersson0884/overtime?style=for-the-badge&cacheSeconds=60
[repo-size-url]: https://github.com/erikpersson0884/overtime

[author-shield]: https://img.shields.io/badge/Author-Erik_Persson-blue?style=for-the-badge
[author-url]: https://github.com/erikpersson0884

[build-shield]: https://img.shields.io/github/actions/workflow/status/erikpersson0884/overtime/build-and-push.yml?branch=main&style=for-the-badge
[build-url]: https://github.com/erikpersson0884/overtime/actions

[tech-1-shield]: https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=for-the-badge
[tech-1-url]: https://www.python.org/
[tech-2-shield]: https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white&style=for-the-badge
[tech-2-url]: https://flask.palletsprojects.com/
[tech-3-shield]: https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white&style=for-the-badge
[tech-3-url]: https://www.sqlite.org/
