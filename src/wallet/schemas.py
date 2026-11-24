from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WalletResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner: str
    balance: Decimal
    currency: str


class TransferRequestDTO(BaseModel):
    sender_wallet_id: int
    recipient_wallet_id: int
    amount: Decimal = Field(gt=0)


class TransferResponseDTO(BaseModel):
    sender_wallet: WalletResponseDTO
    recipient_wallet: WalletResponseDTO
    amount: Decimal
    currency: str


class WalletTransferHistoryDTO(BaseModel):
    id: int
    amount: Decimal
    status: Literal["completed"]
    type: Literal["incoming", "outgoing"]
    created_at: datetime
