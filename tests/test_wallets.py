from decimal import Decimal
from unittest.mock import patch

from starlette.testclient import TestClient

from main import app


client = TestClient(app)


def test_get_wallet_success():
    fake_wallet = {
        "id": 1,
        "owner": "Ahmed Ali",
        "balance": Decimal("3100.00"),
        "currency": "DZD",
    }

    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.get_wallet.return_value = fake_wallet

        response = client.get("/wallets/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "owner": "Ahmed Ali",
        "balance": "3100.00",
        "currency": "DZD",
    }


def test_get_wallet_not_found():
    with patch("src.wallet.routes.get_wallet_service") as mock_service:
        mock_service.return_value.get_wallet.return_value = None

        response = client.get("/wallets/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Wallet not found"
    }