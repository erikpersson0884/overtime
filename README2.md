# Overtime tracker

Small Flask + SQLite app. One user, login required, runs on port 8000.

## Environment variables
| Name | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes | Long random string (`openssl rand -hex 32`). Changing it logs you out. |
| `APP_USERNAME` | yes | Your login name. |
| `APP_PASSWORD_HASH` | yes* | Hashed password, see below. |
| `APP_PASSWORD` | alt* | Plain password, used only if no hash is set. |
| `COOKIE_SECURE` | no | Defaults to `true` (HTTPS only). Set `false` only for local testing over http. |
| `DB_PATH` | no | Defaults to `/data/overtime.db`. |

## Make a password hash
    docker run --rm -it python:3.12-slim sh -c "pip install -q werkzeug && python -c 'import getpass; from werkzeug.security import generate_password_hash as g; print(g(getpass.getpass()))'"

The hash contains `$` characters. In a `.env` file wrap it in single quotes.
If your stack tooling mangles it, use `APP_PASSWORD` instead.

## Data
Everything lives in the `/data` volume (`overtime.db`). Back up by copying that file.

## Run locally
    docker build -t overtime .
    docker run --rm -p 8000:8000 -e COOKIE_SECURE=false -e SECRET_KEY=dev -e APP_USERNAME=me -e APP_PASSWORD=test -v overtime-data:/data overtime
