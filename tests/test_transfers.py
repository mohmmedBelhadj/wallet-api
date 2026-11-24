from decimal import Decimal
from unittest.mock import patch

from starlette.testclient import TestClient

from main import app

client = TestClient(app)


def test_transfer_success():
    sender = {
        "id": 1,
        "owner": "Ahmed Ali",
        "balance": Decimal("2600.00"),
        "currency": "DZD",
    }
    recipient = {
        "id": 2,
        "owner": "Mohamed Omer",
        "balance": Decimal("4000.00"),
        "currency": "DZD",
    }

    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.transfer.return_value = (
            sender,
            recipient,
        )

        response = client.post(
            "/transfers",
            json={
                "sender_wallet_id": 1,
                "recipient_wallet_id": 2,
                "amount": "500.00",
            },
        )

    assert response.status_code == 200
    assert response.json()["sender_wallet"]["balance"] == "2600.00"
    assert response.json()["recipient_wallet"]["balance"] == "4000.00"
    assert response.json()["amount"] == "500.00"
    assert response.json()["currency"] == "DZD"


def test_transfer_zero_amount():
    response = client.post(
        "/transfers",
        json={
            "sender_wallet_id": 1,
            "recipient_wallet_id": 2,
            "amount": "0",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data"}


def test_transfer_missing_field():
    response = client.post(
        "/transfers",
        json={
            "sender_wallet_id": 1,
            "amount": "500",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request data"}


def test_transfer_wallet_not_found():
    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.transfer.side_effect = LookupError("Wallet not found")

        response = client.post(
            "/transfers",
            json={
                "sender_wallet_id": 1,
                "recipient_wallet_id": 999,
                "amount": "500",
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Wallet not found"}


def test_transfer_insufficient_funds():
    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.transfer.side_effect = ArithmeticError(
            "Insufficient funds"
        )

        response = client.post(
            "/transfers",
            json={
                "sender_wallet_id": 1,
                "recipient_wallet_id": 2,
                "amount": "5000",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Insufficient funds"}


def test_transfer_same_wallet():
    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.transfer.side_effect = ValueError(
            "Cannot transfer to the same wallet"
        )

        response = client.post(
            "/transfers",
            json={
                "sender_wallet_id": 1,
                "recipient_wallet_id": 1,
                "amount": "500",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot transfer to the same wallet"}


def test_transfer_different_currencies():
    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.transfer.side_effect = ValueError(
            "Wallet currencies do not match"
        )

        response = client.post(
            "/transfers",
            json={
                "sender_wallet_id": 1,
                "recipient_wallet_id": 2,
                "amount": "500",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Wallet currencies do not match"}
