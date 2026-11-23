import os
from decimal import Decimal

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict, make_conninfo

load_dotenv()


@pytest.fixture
def test_database_url():
    params = conninfo_to_dict(os.environ["DATABASE_URL"])
    params["dbname"] = "wallet_test_db"
    return make_conninfo(**params)


@pytest.fixture
def db_connection(test_database_url):
    with psycopg.connect(test_database_url) as conn:
        yield conn


@pytest.fixture
def wallet_data(db_connection):
    with db_connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (full_name, email)
            VALUES
                ('Test Sender', 'sender@test.local'),
                ('Test Recipient', 'recipient@test.local')
            RETURNING id
            """
        )
        user_ids = [row[0] for row in cur.fetchall()]

        cur.execute(
            """
            INSERT INTO wallets (user_id, balance, currency)
            VALUES
                (%s, %s, %s),
                (%s, %s, %s)
            RETURNING id
            """,
            (
                user_ids[0],
                Decimal("5000.00"),
                "DZD",
                user_ids[1],
                Decimal("2000.00"),
                "DZD",
            ),
        )
        wallet_ids = [row[0] for row in cur.fetchall()]

    # Commit fixture data so independent repository connections can see it.
    db_connection.commit()

    yield {
        "sender_wallet_id": wallet_ids[0],
        "recipient_wallet_id": wallet_ids[1],
    }

    # Clean up transfers, wallets, and users after the test.
    with db_connection.cursor() as cur:
        cur.execute(
            """
            DELETE FROM transfers
            WHERE sender_wallet_id IN (%s, %s)
               OR recipient_wallet_id IN (%s, %s)
            """,
            (
                wallet_ids[0],
                wallet_ids[1],
                wallet_ids[0],
                wallet_ids[1],
            ),
        )

        cur.execute(
            "DELETE FROM wallets WHERE id IN (%s, %s)",
            (wallet_ids[0], wallet_ids[1]),
        )

        cur.execute(
            "DELETE FROM users WHERE id IN (%s, %s)",
            (user_ids[0], user_ids[1]),
        )

    db_connection.commit()


@pytest.fixture
def reject_transfer_insert(db_connection):
    with db_connection.cursor() as cur:
        cur.execute("""
            CREATE OR REPLACE FUNCTION reject_transfer_insert_for_test()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Forced failure during transfer insertion';
            END;
            $$ LANGUAGE plpgsql;
        """)

        cur.execute("""
            CREATE TRIGGER test_reject_transfer_insert
            BEFORE INSERT ON transfers
            FOR EACH ROW
            EXECUTE FUNCTION reject_transfer_insert_for_test();
        """)

    db_connection.commit()

    try:
        yield
    finally:
        with db_connection.cursor() as cur:
            cur.execute("""
                DROP TRIGGER IF EXISTS test_reject_transfer_insert
                ON transfers;
            """)
            cur.execute("""
                DROP FUNCTION IF EXISTS reject_transfer_insert_for_test();
            """)

        db_connection.commit()
