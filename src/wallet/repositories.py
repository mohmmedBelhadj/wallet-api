import os
from decimal import Decimal

from dotenv import load_dotenv
import psycopg


load_dotenv()


class WalletRepository:
    def __init__(self):
        self.database_url = os.environ["DATABASE_URL"]

    def get_by_id(self, wallet_id: int):
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        w.id,
                        u.full_name AS owner,
                        w.balance,
                        w.currency
                    FROM wallets AS w
                    JOIN users AS u ON u.id = w.user_id
                    WHERE w.id = %s
                    """,
                    (wallet_id,),
                )

                row = cur.fetchone()

                if row is None:
                    return None

                return {
                    "id": row[0],
                    "owner": row[1],
                    "balance": row[2],
                    "currency": row[3],
                }

    def get_all(self):
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        w.id,
                        u.full_name AS owner,
                        w.balance,
                        w.currency
                    FROM wallets AS w
                    JOIN users AS u ON u.id = w.user_id
                    ORDER BY w.id
                    """
                )

                rows = cur.fetchall()

                return [
                    {
                        "id": row[0],
                        "owner": row[1],
                        "balance": row[2],
                        "currency": row[3],
                    }
                    for row in rows
                ]

    def transfer(
        self,
        sender_wallet_id: int,
        recipient_wallet_id: int,
        amount: Decimal,
    ):
        if sender_wallet_id == recipient_wallet_id:
            raise ValueError("Cannot transfer to the same wallet")

        if amount <= 0:
            raise ValueError("Amount must be greater than zero")

        with psycopg.connect(self.database_url) as conn:
            with conn.transaction():
                with conn.cursor() as cur:

                    # Lock both wallets in a consistent order.
                    wallet_ids = sorted(
                        [sender_wallet_id, recipient_wallet_id]
                    )

                    cur.execute(
                        """
                        SELECT id, balance, currency
                        FROM wallets
                        WHERE id IN (%s, %s)
                        ORDER BY id
                        FOR UPDATE
                        """,
                        (wallet_ids[0], wallet_ids[1]),
                    )

                    rows = cur.fetchall()

                    if len(rows) != 2:
                        raise LookupError("Wallet not found")

                    wallets = {
                        row[0]: {
                            "balance": row[1],
                            "currency": row[2],
                        }
                        for row in rows
                    }

                    sender = wallets[sender_wallet_id]
                    recipient = wallets[recipient_wallet_id]

                    if sender["currency"] != recipient["currency"]:
                        raise ValueError("Wallet currencies do not match")

                    if sender["balance"] < amount:
                        raise ArithmeticError("Insufficient funds")

                    # Deduct from sender.
                    cur.execute(
                        """
                        UPDATE wallets
                        SET balance = balance - %s
                        WHERE id = %s
                        """,
                        (amount, sender_wallet_id),
                    )

                    # Add to recipient.
                    cur.execute(
                        """
                        UPDATE wallets
                        SET balance = balance + %s
                        WHERE id = %s
                        """,
                        (amount, recipient_wallet_id),
                    )

                    # Record the transfer.
                    cur.execute(
                        """
                        INSERT INTO transfers (
                            sender_wallet_id,
                            recipient_wallet_id,
                            amount
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            sender_wallet_id,
                            recipient_wallet_id,
                            amount,
                        ),
                    )

                    # Read the updated wallets for the API response.
                    sender_wallet = self._get_wallet(cur, sender_wallet_id)
                    recipient_wallet = self._get_wallet(cur, recipient_wallet_id)

                    return sender_wallet, recipient_wallet

    @staticmethod
    def _get_wallet(cur, wallet_id: int):
        cur.execute(
            """
            SELECT
                w.id,
                u.full_name AS owner,
                w.balance,
                w.currency
            FROM wallets AS w
            JOIN users AS u ON u.id = w.user_id
            WHERE w.id = %s
            """,
            (wallet_id,),
        )

        row = cur.fetchone()

        return {
            "id": row[0],
            "owner": row[1],
            "balance": row[2],
            "currency": row[3],
        }
