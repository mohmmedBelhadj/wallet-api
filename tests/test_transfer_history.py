from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.wallet.schemas import WalletTransferHistoryDTO


def test_wallet_transfer_history_dto_valid():
    create_time = datetime.now()
    wallet_transfer_history_dto = WalletTransferHistoryDTO(
        id=1,
        type="outgoing",
        amount=Decimal("100.00"),
        status="completed",
        created_at=create_time,
    )
    assert wallet_transfer_history_dto.id == 1
    assert wallet_transfer_history_dto.type == "outgoing"
    assert wallet_transfer_history_dto.amount == Decimal("100.00")
    assert wallet_transfer_history_dto.status == "completed"
    assert wallet_transfer_history_dto.created_at == create_time


def test_wallet_transfer_history_dto_invalid():
    with pytest.raises(ValidationError):
        WalletTransferHistoryDTO.model_validate(
            {
                "id": 1,
                "type": "unknown",
                "amount": Decimal("100.00"),
                "status": "completed",
                "created_at": datetime.now(),
            }
        )
