from fastapi import APIRouter
from app.services.solana_client import get_payer_balance

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    try:
        balance = await get_payer_balance()
        solana_status = "ok"
    except Exception as exc:
        balance = None
        solana_status = f"error: {exc}"

    return {
        "status": "ok",
        "service": "solana-agent-mvp",
        "solana": solana_status,
        "payer_balance_sol": balance,
    }
