from decimal import Decimal

from src.wallet.repositories import WalletRepository


class WalletService:
    def __init__(self, repository: WalletRepository):
        self.repository = repository

    def get_wallet(self, wallet_id: int):
        return self.repository.get_by_id(wallet_id)

    def get_wallets(self):
        return self.repository.get_all()

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

        return self.repository.transfer(
            sender_wallet_id=sender_wallet_id,
            recipient_wallet_id=recipient_wallet_id,
            amount=amount,
        )