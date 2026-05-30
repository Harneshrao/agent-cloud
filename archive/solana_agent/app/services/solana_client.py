"""
Solana payment client.

Responsibilities:
  - Load the payer keypair from config (base58 private key)
  - Build a SOL transfer transaction
  - Send and confirm the transaction
  - Return the transaction signature string

Uses solana-py (solana + solders) — pure Python, no Node.js required.
"""

import logging
from dataclasses import dataclass

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from app.core.config import settings

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000


@dataclass
class PaymentResult:
    success: bool
    signature: str
    error: str | None = None


def _load_payer() -> Keypair:
    """Load keypair from base58-encoded private key in config."""
    return Keypair.from_base58_string(settings.SOLANA_PAYER_PRIVATE_KEY)


def _sol_to_lamports(amount_sol: float) -> int:
    return int(amount_sol * LAMPORTS_PER_SOL)


async def send_payment(recipient_address: str, amount_sol: float) -> PaymentResult:
    """
    Send `amount_sol` SOL from the payer wallet to `recipient_address`.
    Returns a PaymentResult with the transaction signature on success.
    """
    payer = _load_payer()
    recipient = Pubkey.from_string(recipient_address)
    lamports = _sol_to_lamports(amount_sol)

    logger.info(
        "Sending %.9f SOL (%d lamports) to %s", amount_sol, lamports, recipient_address
    )

    async with AsyncClient(settings.SOLANA_RPC_URL) as client:
        # Fetch latest blockhash (required for every transaction)
        blockhash_resp = await client.get_latest_blockhash(commitment=Confirmed)
        recent_blockhash: Hash = blockhash_resp.value.blockhash

        # Build the transfer instruction
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=payer.pubkey(),
                to_pubkey=recipient,
                lamports=lamports,
            )
        )

        # Build and sign the transaction
        message = Message([transfer_ix], payer.pubkey())
        tx = Transaction([payer], message, recent_blockhash)

        # Send and wait for confirmation
        resp = await client.send_transaction(
            tx,
            opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed),
        )

        signature = str(resp.value)
        logger.info("Transaction confirmed: %s", signature)
        return PaymentResult(success=True, signature=signature)


async def get_payer_balance() -> float:
    """Return the payer wallet balance in SOL. Useful for health checks."""
    payer = _load_payer()
    async with AsyncClient(settings.SOLANA_RPC_URL) as client:
        resp = await client.get_balance(payer.pubkey(), commitment=Confirmed)
        return resp.value / LAMPORTS_PER_SOL
