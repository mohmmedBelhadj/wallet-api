# Wallet API: Project Context

## Purpose

This repository contains an early-stage Python HTTP API for looking up wallet balances and transferring funds between wallets. It uses Starlette for routing, Pydantic for request/response validation, and PostgreSQL through Psycopg.

## Project layout

- `main.py` builds the Starlette application and registers `/health` plus wallet routes.
- `src/wallet/routes.py` implements HTTP handlers and maps service errors to HTTP responses.
- `src/wallet/services.py` contains wallet lookup and transfer business logic.
- `src/wallet/repositories.py` contains PostgreSQL access for wallet lookup and is intended to persist wallet changes.
- `src/wallet/schemas.py` defines Pydantic DTOs for wallets and transfers.
- `src/wallet/models.py` currently has no model definitions.
- `test_db.py` is a standalone database query script, not an automated test suite.
- `pyproject.toml` declares Python 3.13+ and dependencies; `uv.lock` locks them.

## Current API surface

| Method | Path | Intended behavior |
| --- | --- | --- |
| `GET` | `/health` | Return `{"status":"ok"}`. |
| `GET` | `/wallets/{wallet_id}` | Return wallet ID, owner, balance, and currency; 404 if missing. |
| `POST` | `/transfers` | Accept `sender_wallet_id`, `recipient_wallet_id`, and positive `amount`; transfer funds and return both updated wallets and transfer details. |

Transfer request and response shapes are declared in `src/wallet/schemas.py`. Amounts use `Decimal` at the API boundary. The repository's lookup joins `wallets` with `users`, using `users.full_name` for the wallet owner.

## Request flow

For wallet operations, the route constructs a `WalletRepository` and `WalletService`. The service reads wallet rows, applies basic transfer rules (different wallets and sufficient sender balance), adjusts the in-memory balances, and calls repository persistence. The route serializes results through Pydantic and returns JSON.

## Configuration and data assumptions

The repository reads its PostgreSQL connection string from the `DATABASE_URL` environment variable. No schema migrations, database setup instructions, connection lifecycle management, or transaction handling are present. The SQL implies `wallets(id, user_id, balance, currency)` and `users(id, full_name)` tables. The standalone `test_db.py` queries a `users` table and assumes a local database is available.

## Known incomplete or broken areas

- `WalletRepository.save()` is called by transfers but is not implemented, so a valid transfer currently fails at persistence.
- The transfer route creates a `TransferResponseDTO` but then returns a response using an undefined variable (`wallet`) and the wallet-only DTO. The successful transfer response path therefore fails and does not match the declared transfer response shape.
- Transfer logic does not check that sender and recipient use the same currency.
- The two balance updates are not wrapped in a database transaction and do not lock rows, so partial writes or concurrent balance races are possible once persistence is implemented.
- The API creates a new repository/connection per request and does not close that connection explicitly.
- `WalletService.transfer` annotates `amount` as `int` despite receiving a Pydantic `Decimal` amount.
- There is no automated test suite or documented run/deploy workflow in the repository at present.

## Running locally

The dependency metadata indicates the app can be served as an ASGI application at `main:app` with Uvicorn. A working PostgreSQL instance and compatible schema are needed for wallet endpoints. The health endpoint itself does not access the database. No setup command or database bootstrap is documented yet.

## Practical next steps

1. Add database setup/schema guidance and validate required configuration at startup.
2. Implement repository persistence with explicit transaction and connection handling.
3. Correct the successful transfer response and enforce currency compatibility.
4. Add automated tests for validat
5. ion, not-found cases, insufficient funds, and successful transfers.
5. Expand the README with installation and local run instructions.
