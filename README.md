uv run python - <<'PY'
import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path
from psycopg.conninfo import conninfo_to_dict, make_conninfo

load_dotenv(Path(".env"))

params = conninfo_to_dict(os.environ["DATABASE_URL"])
params["dbname"] = "wallet_test_db"
test_url = make_conninfo(**params)

statements = [
    """
    CREATE TABLE users (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        full_name varchar(100) NOT NULL,
        email varchar(255) NOT NULL UNIQUE,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE wallets (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id bigint NOT NULL UNIQUE,
        balance numeric(18,2) NOT NULL DEFAULT 0.00,
        currency varchar(3) NOT NULL DEFAULT 'DZD',
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT check_wallet_balance CHECK (balance >= 0),
        CONSTRAINT fk_wallet_user
            FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE transfers (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        sender_wallet_id bigint NOT NULL,
        recipient_wallet_id bigint NOT NULL,
        amount numeric(18,2) NOT NULL,
        status varchar(20) NOT NULL DEFAULT 'completed',
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT check_different_wallets
            CHECK (sender_wallet_id <> recipient_wallet_id),
        CONSTRAINT check_transfer_amount CHECK (amount > 0),
        CONSTRAINT check_transfer_status
            CHECK (status IN ('pending', 'completed', 'failed')),
        CONSTRAINT fk_sender_wallet
            FOREIGN KEY (sender_wallet_id) REFERENCES wallets(id),
        CONSTRAINT fk_recipient_wallet
            FOREIGN KEY (recipient_wallet_id) REFERENCES wallets(id)
    )
    """,
]

with psycopg.connect(test_url) as conn:
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print("Created tables:")
        for row in cur.fetchall():
            print("-", row[0])

PY