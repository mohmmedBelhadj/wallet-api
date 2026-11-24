from pydantic import ValidationError
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.wallet.repositories import WalletRepository
from src.wallet.schemas import (
    TransferRequestDTO,
    TransferResponseDTO,
    WalletResponseDTO,
    WalletTransferHistoryDTO,
)
from src.wallet.services import WalletService


def get_wallet_service():
    repository = WalletRepository()
    return WalletService(repository)


async def get_wallet(request):
    wallet_id = int(request.path_params["wallet_id"])

    service = get_wallet_service()
    wallet = service.get_wallet(wallet_id)

    if wallet is None:
        return JSONResponse(
            {"detail": "Wallet not found"},
            status_code=404,
        )

    return JSONResponse(
        WalletResponseDTO.model_validate(wallet).model_dump(mode="json")
    )


async def get_wallets(request):
    service = get_wallet_service()
    wallets = service.get_wallets()

    response = [
        WalletResponseDTO.model_validate(wallet).model_dump(mode="json")
        for wallet in wallets
    ]

    return JSONResponse(response)


async def create_transfer(request):
    try:
        payload = await request.json()
        transfer_request = TransferRequestDTO.model_validate(payload)
    except (ValueError, ValidationError):
        return JSONResponse(
            {"detail": "Invalid request data"},
            status_code=422,
        )

    service = get_wallet_service()

    try:
        sender, recipient = service.transfer(
            sender_wallet_id=transfer_request.sender_wallet_id,
            recipient_wallet_id=transfer_request.recipient_wallet_id,
            amount=transfer_request.amount,
        )
    except LookupError:
        return JSONResponse(
            {"detail": "Wallet not found"},
            status_code=404,
        )
    except ArithmeticError:
        return JSONResponse(
            {"detail": "Insufficient funds"},
            status_code=400,
        )
    except ValueError as exc:
        return JSONResponse(
            {"detail": str(exc)},
            status_code=400,
        )

    response = TransferResponseDTO(
        sender_wallet=sender,
        recipient_wallet=recipient,
        amount=transfer_request.amount,
        currency=sender["currency"],
    )

    return JSONResponse(response.model_dump(mode="json"))


async def get_wallet_transfers(request):
    wallet_id = int(request.path_params["wallet_id"])
    service = get_wallet_service()

    transfers = service.get_wallet_transfers(wallet_id)
    if transfers is None:
        return JSONResponse(
            {"detail": "Wallet not found"},
            status_code=404,
        )

    response = [
        WalletTransferHistoryDTO.model_validate(transfer).model_dump(mode="json")
        for transfer in transfers
    ]

    return JSONResponse(response)


routes = [
    Route(
        "/wallets/{wallet_id:int}",
        get_wallet,
        methods=["GET"],
    ),
    Route(
        "/wallets",
        get_wallets,
        methods=["GET"],
    ),
    Route(
        "/transfers",
        create_transfer,
        methods=["POST"],
    ),
    Route(
        "/wallets/{wallet_id:int}/transfers",
        get_wallet_transfers,
        methods=["GET"],
    ),
]
