from decimal import Decimal

import psycopg
import pytest
from starlette.testclient import TestClient

from main import app
from src.wallet.repositories import WalletRepository

client = TestClient(app)


def test_transfer_updates_database(
    monkeypatch,
    test_database_url,
    db_connection,
    wallet_data,
):
    # Direct the application to the test database.
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    response = client.post(
        "/transfers",
        json={
            "sender_wallet_id": sender_id,
            "recipient_wallet_id": recipient_id,
            "amount": "500.00",
        },
    )

    assert response.status_code == 200

    # Verify actual balances in PostgreSQL.
    with db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, balance
            FROM wallets
            WHERE id IN (%s, %s)
            ORDER BY id
            """,
            (sender_id, recipient_id),
        )
        balances = dict(cur.fetchall())

        cur.execute(
            """
            SELECT sender_wallet_id, recipient_wallet_id, amount, status
            FROM transfers
            WHERE sender_wallet_id = %s
              AND recipient_wallet_id = %s
            ORDER BY id DESC LIMIT 1
            """,
            (sender_id, recipient_id),
        )
        transfer = cur.fetchone()

    assert balances[sender_id] == Decimal("4500.00")
    assert balances[recipient_id] == Decimal("2500.00")

    assert transfer is not None
    assert transfer == (
        sender_id,
        recipient_id,
        Decimal("500.00"),
        "completed",
    )


def test_transfer_insufficient_funds_does_not_change_database(
    monkeypatch,
    test_database_url,
    db_connection,
    wallet_data,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    # Set the sender's balance to 100 DZD.
    with db_connection.cursor() as cur:
        cur.execute(
            "UPDATE wallets SET balance = %s WHERE id = %s",
            (Decimal("100.00"), sender_id),
        )
    db_connection.commit()

    # Attempt to transfer 500 DZD.
    response = client.post(
        "/transfers",
        json={
            "sender_wallet_id": sender_id,
            "recipient_wallet_id": recipient_id,
            "amount": "500.00",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Insufficient funds"}

    # Verify that balances and transfer records remain unchanged.
    with db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, balance
            FROM wallets
            WHERE id IN (%s, %s)
            """,
            (sender_id, recipient_id),
        )
        balances = dict(cur.fetchall())

        cur.execute(
            """
            SELECT COUNT(*)
            FROM transfers
            WHERE sender_wallet_id = %s
              AND recipient_wallet_id = %s
            """,
            (sender_id, recipient_id),
        )
        transfer_count = cur.fetchone()[0]

    assert balances[sender_id] == Decimal("100.00")
    assert balances[recipient_id] == Decimal("2000.00")
    assert transfer_count == 0


def test_transfer_different_currencies_does_not_change_database(
    monkeypatch,
    test_database_url,
    db_connection,
    wallet_data,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    # Change the recipient wallet currency to USD.
    with db_connection.cursor() as cur:
        cur.execute(
            "UPDATE wallets SET currency = %s WHERE id = %s",
            ("USD", recipient_id),
        )
    db_connection.commit()

    response = client.post(
        "/transfers",
        json={
            "sender_wallet_id": sender_id,
            "recipient_wallet_id": recipient_id,
            "amount": "500.00",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Wallet currencies do not match"}

    # Verify that balances remain unchanged and no transfer was created.
    with db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, balance, currency
            FROM wallets
            WHERE id IN (%s, %s)
            """,
            (sender_id, recipient_id),
        )
        wallets = {
            row[0]: {"balance": row[1], "currency": row[2]} for row in cur.fetchall()
        }

        cur.execute(
            """
            SELECT COUNT(*)
            FROM transfers
            WHERE sender_wallet_id = %s
              AND recipient_wallet_id = %s
            """,
            (sender_id, recipient_id),
        )
        transfer_count = cur.fetchone()[0]

    assert wallets[sender_id] == {
        "balance": Decimal("5000.00"),
        "currency": "DZD",
    }
    assert wallets[recipient_id] == {
        "balance": Decimal("2000.00"),
        "currency": "USD",
    }
    assert transfer_count == 0


def test_transfer_rolls_back_when_insert_fails(
    monkeypatch,
    test_database_url,
    db_connection,
    wallet_data,
    reject_transfer_insert,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    # The database trigger will force the INSERT to fail.
    with pytest.raises(
        psycopg.Error,
        match="Forced failure during transfer insertion",
    ):
        client.post(
            "/transfers",
            json={
                "sender_wallet_id": sender_id,
                "recipient_wallet_id": recipient_id,
                "amount": "500.00",
            },
        )

    # Verify that the entire transaction was rolled back.
    with db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, balance
            FROM wallets
            WHERE id IN (%s, %s)
            """,
            (sender_id, recipient_id),
        )
        balances = dict(cur.fetchall())

        cur.execute(
            """
            SELECT COUNT(*)
            FROM transfers
            WHERE sender_wallet_id = %s
              AND recipient_wallet_id = %s
            """,
            (sender_id, recipient_id),
        )
        transfer_count = cur.fetchone()[0]

    assert balances[sender_id] == Decimal("5000.00")
    assert balances[recipient_id] == Decimal("2000.00")
    assert transfer_count == 0


def test_get_wallets_from_database(
    monkeypatch,
    test_database_url,
    wallet_data,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    response = client.get("/wallets")

    assert response.status_code == 200

    wallets = response.json()

    assert len(wallets) == 2

    wallets_by_id = {wallet["id"]: wallet for wallet in wallets}

    assert wallets_by_id[sender_id] == {
        "id": sender_id,
        "owner": "Test Sender",
        "balance": "5000.00",
        "currency": "DZD",
    }

    assert wallets_by_id[recipient_id] == {
        "id": recipient_id,
        "owner": "Test Recipient",
        "balance": "2000.00",
        "currency": "DZD",
    }


def test_get_wallet_transfers_from_database(
    monkeypatch,
    test_database_url,
    db_connection,
    wallet_data,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]
    recipient_id = wallet_data["recipient_wallet_id"]

    with db_connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transfers (sender_wallet_id,
                                   recipient_wallet_id,
                                   amount,
                                   created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                sender_id,
                recipient_id,
                Decimal("500.00"),
                "2026-11-20T10:00:00+00:00",
            ),
        )

        cur.execute(
            """
            INSERT INTO transfers (sender_wallet_id,
                                   recipient_wallet_id,
                                   amount,
                                   created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                recipient_id,
                sender_id,
                Decimal("200.00"),
                "2026-11-21T10:00:00+00:00",
            ),
        )

    db_connection.commit()

    transfers = WalletRepository().get_transfers_by_wallet_id(sender_id)

    assert len(transfers) == 2

    assert transfers[0]["amount"] == Decimal("200.00")
    assert transfers[0]["type"] == "incoming"

    assert transfers[1]["amount"] == Decimal("500.00")
    assert transfers[1]["type"] == "outgoing"

    assert all(transfer["status"] == "completed" for transfer in transfers)


def test_get_transfers_empty(
    monkeypatch,
    test_database_url,
    wallet_data,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    sender_id = wallet_data["sender_wallet_id"]

    transfers = WalletRepository().get_transfers_by_wallet_id(sender_id)

    assert transfers == []


def test_get_transfers_wallet_not_found(
    monkeypatch,
    test_database_url,
):
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    transfers = WalletRepository().get_transfers_by_wallet_id(999999)

    assert transfers is None
