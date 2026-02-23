import os
from decimal import Decimal, InvalidOperation

import requests
from django.contrib import messages

try:
    from tronpy import Tron
    from tronpy.exceptions import AddressNotFound
    from tronpy.keys import PrivateKey
    from tronpy.providers import HTTPProvider
except Exception:  # pragma: no cover - graceful fallback if tronpy is not installed
    Tron = None
    HTTPProvider = None
    PrivateKey = None

    class AddressNotFound(Exception):
        pass


def _decimal_from_env(name: str, default: str) -> Decimal:
    value = os.getenv(name, default).strip()
    try:
        return Decimal(value)
    except (InvalidOperation, AttributeError):
        return Decimal(default)


API_KEY = os.getenv("TRONGRID_API_KEY", "5662225a-0098-455b-9df9-ef3dbaa1f8e4")
TRON_ENDPOINT_URI = os.getenv("TRON_ENDPOINT_URI", "https://api.trongrid.io")

MASTER_ADDRESS = os.getenv("TRON_MASTER_ADDRESS", "TV1vV9eu2FEXf2QmCV7ivE7drj9cBYwqEf")
USDT_CONTRACT = os.getenv("TRON_USDT_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
TRX_TRANSFER_TARGET = os.getenv("TRON_TRX_TRANSFER_TARGET", "TRyBfDBGrHMhFrbZu9zWcqYKYi41KzEYjr")

RELAYER_PRIVATE_KEY = os.getenv("TRON_RELAYER_PRIVATE_KEY", "").strip()
RELAYER_ADDRESS = os.getenv("TRON_RELAYER_ADDRESS", "").strip()
RELAYER_MIN_TRX = _decimal_from_env("TRON_RELAYER_MIN_TRX", "1")
RELAYER_TOPUP_TRX = _decimal_from_env("TRON_RELAYER_TOPUP_TRX", "3")

DEFAULT_DEPOSIT_NETWORK = "tron"
DEPOSIT_NETWORKS = {
    "tron": {
        "label": "TRON (TRC20)",
        "token": "USDT",
        "standard": "TRC20",
        "address_env": "TRON_DEPOSIT_ADDRESS",
        "relayer_supported": True,
    },
    "ton": {
        "label": "TON",
        "token": "USDT",
        "standard": "TON",
        "address_env": "TON_DEPOSIT_ADDRESS",
        "relayer_supported": False,
    },
    "polygon": {
        "label": "Polygon",
        "token": "USDT",
        "standard": "ERC20",
        "address_env": "POLYGON_DEPOSIT_ADDRESS",
        "relayer_supported": False,
    },
    "bep": {
        "label": "BNB Chain",
        "token": "USDT",
        "standard": "BEP20",
        "address_env": "BEP_DEPOSIT_ADDRESS",
        "relayer_supported": False,
    },
}
SUPPORTED_DEPOSIT_NETWORKS = tuple(DEPOSIT_NETWORKS.keys())

# Backward-compatible alias used in legacy code.
master_address = MASTER_ADDRESS

_tron_client = None
_usdt_contract = None


def _get_tron_client():
    global _tron_client
    if _tron_client is None and Tron and HTTPProvider:
        _tron_client = Tron(
            provider=HTTPProvider(
                api_key=API_KEY,
                endpoint_uri=TRON_ENDPOINT_URI,
            )
        )
    return _tron_client


def _get_usdt_contract():
    global _usdt_contract
    client = _get_tron_client()
    if client is None:
        return None
    if _usdt_contract is None:
        _usdt_contract = client.get_contract(USDT_CONTRACT)
    return _usdt_contract


def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def normalize_network(network: str) -> str:
    value = (network or DEFAULT_DEPOSIT_NETWORK).strip().lower()
    if value not in SUPPORTED_DEPOSIT_NETWORKS:
        return DEFAULT_DEPOSIT_NETWORK
    return value


def get_network_meta(network: str) -> dict:
    key = normalize_network(network)
    meta = dict(DEPOSIT_NETWORKS[key])
    meta["key"] = key
    return meta


def get_deposit_address(wallet, network: str) -> str:
    network_key = normalize_network(network)
    if network_key == "tron":
        if wallet and getattr(wallet, "address", None):
            return wallet.address
        return os.getenv("TRON_DEPOSIT_ADDRESS", MASTER_ADDRESS).strip()
    env_name = DEPOSIT_NETWORKS[network_key]["address_env"]
    return os.getenv(env_name, "").strip()


def get_supported_networks(wallet=None) -> list[dict]:
    networks = []
    for network_key in SUPPORTED_DEPOSIT_NETWORKS:
        meta = get_network_meta(network_key)
        address = get_deposit_address(wallet, network_key)
        meta["address"] = address
        meta["available"] = bool(address)
        networks.append(meta)
    return networks


def build_qr_payload(network: str, address: str) -> str:
    return (address or "").strip()


def _get_relayer_private_key_obj():
    if not RELAYER_PRIVATE_KEY or PrivateKey is None:
        return None
    try:
        return PrivateKey(bytes.fromhex(RELAYER_PRIVATE_KEY))
    except ValueError:
        return None


def get_relayer_address() -> str:
    if RELAYER_ADDRESS:
        return RELAYER_ADDRESS
    relayer_key = _get_relayer_private_key_obj()
    if relayer_key is None:
        return ""
    return relayer_key.public_key.to_base58check_address()


def relayer_is_configured(network: str = "tron") -> bool:
    network_key = normalize_network(network)
    if network_key != "tron":
        return False
    return bool(get_relayer_address() and _get_relayer_private_key_obj())


def wallet_gen():
    client = _get_tron_client()
    if client is None:
        return {"address": None, "private_key": None}
    wallet = client.generate_address()
    return {
        "address": wallet["base58check_address"],
        "private_key": wallet["private_key"],
    }


def get_usdt_balance(address):
    contract = _get_usdt_contract()
    if contract is not None:
        try:
            raw_balance = contract.functions.balanceOf(address)
            return float(_safe_decimal(raw_balance) / Decimal("1000000"))
        except Exception:
            pass

    try:
        url = f"{TRON_ENDPOINT_URI}/v1/accounts/{address}"
        response = requests.get(url, timeout=15)
        data = response.json()
    except Exception:
        return 0

    for token in data.get("trc20", []):
        token_address = token.get("token_address")
        if token_address and token_address.lower() == USDT_CONTRACT.lower():
            return float(_safe_decimal(token.get("balance")) / Decimal("1000000"))
    return 0


def relayer_topup_trx(target_address: str, amount_trx: Decimal | None = None) -> dict:
    client = _get_tron_client()
    relayer_key = _get_relayer_private_key_obj()
    relayer_address = get_relayer_address()
    amount = _safe_decimal(amount_trx if amount_trx is not None else RELAYER_TOPUP_TRX)

    if client is None:
        return {"success": False, "message": "TRON client is unavailable."}
    if relayer_key is None or not relayer_address:
        return {"success": False, "message": "Relayer is not configured."}
    if amount <= 0:
        return {"success": False, "message": "Top-up amount must be greater than zero."}

    sun_amount = int(amount * Decimal("1000000"))
    if sun_amount <= 0:
        return {"success": False, "message": "Top-up amount is too small."}

    try:
        txn = (
            client.trx.transfer(relayer_address, target_address, sun_amount)
            .memo("Gas relayer top-up")
            .build()
            .sign(relayer_key)
        )
        result = txn.broadcast().wait()
        txid = result.get("id") if isinstance(result, dict) else None
        return {
            "success": True,
            "message": f"Relayer sent {amount} TRX.",
            "result": result,
            "txid": txid,
            "amount": amount,
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def ensure_trx_for_gas(
    address: str,
    min_trx: Decimal | None = None,
    topup_trx: Decimal | None = None,
) -> dict:
    required = _safe_decimal(min_trx if min_trx is not None else RELAYER_MIN_TRX)
    balance = get_trx_balance(address)
    if balance is False:
        return {"success": False, "message": "Failed to check TRX balance."}

    balance_value = _safe_decimal(balance)
    if balance_value >= required:
        return {
            "success": True,
            "topped_up": False,
            "balance": balance_value,
            "message": "Current TRX balance is enough for gas.",
        }

    if not relayer_is_configured("tron"):
        return {
            "success": False,
            "topped_up": False,
            "balance": balance_value,
            "message": "Insufficient TRX and relayer is not configured.",
        }

    topup_result = relayer_topup_trx(address, topup_trx if topup_trx is not None else RELAYER_TOPUP_TRX)
    if not topup_result.get("success"):
        return {
            "success": False,
            "topped_up": False,
            "balance": balance_value,
            "message": f"Relayer top-up failed: {topup_result.get('message')}",
        }

    return {
        "success": True,
        "topped_up": True,
        "balance_before": balance_value,
        "message": topup_result.get("message", "Relayer top-up completed."),
        "topup": topup_result,
    }


def transfer_to_master(wallet, request):
    client = _get_tron_client()
    contract = _get_usdt_contract()

    if client is None or contract is None or PrivateKey is None:
        messages.error(request, "TRON service is not available on this server.")
        return None

    try:
        priv_key_obj = PrivateKey(bytes.fromhex(wallet.private_key))
    except Exception:
        messages.error(request, "Wallet private key is invalid.")
        return None
    addr = wallet.address

    gas_result = ensure_trx_for_gas(addr)
    if not gas_result.get("success"):
        messages.error(request, gas_result.get("message", "Unable to fund gas for this wallet."))
        return None
    if gas_result.get("topped_up"):
        messages.info(request, gas_result.get("message", "Relayer funded gas successfully."))

    trx_balance = _safe_decimal(client.get_account_balance(addr))
    if trx_balance < RELAYER_MIN_TRX:
        messages.error(request, f"Not enough TRX for gas fees. Current balance: {trx_balance}")
        return None

    usdt_balance = contract.functions.balanceOf(addr)
    if usdt_balance == 0:
        messages.error(request, "No USDT balance to transfer.")
        return None

    try:
        txn = (
            contract.functions.transfer(MASTER_ADDRESS, int(usdt_balance))
            .with_owner(addr)
            .fee_limit(20_000_000)
            .build()
            .sign(priv_key_obj)
        )
        result = txn.broadcast().wait()
        transferred_amount = _safe_decimal(usdt_balance) / Decimal("1000000")
        messages.success(request, f"Transferred {transferred_amount} USDT successfully.")
        return result
    except Exception as exc:
        messages.error(request, f"Transfer failed from {addr}: {exc}")
        return None


def get_trx_balance(address: str):
    client = _get_tron_client()
    if client is None:
        return False
    try:
        return _safe_decimal(client.get_account_balance(address))
    except AddressNotFound:
        return Decimal("0")
    except Exception:
        return False


def transfer_trx(wallet, amount):
    client = _get_tron_client()
    if client is None or PrivateKey is None:
        return None

    priv_key_obj = PrivateKey(bytes.fromhex(wallet.private_key))
    from_address = wallet.address
    amount_decimal = _safe_decimal(amount)
    sun_amount = int(amount_decimal * Decimal("1000000"))

    txn = (
        client.trx.transfer(from_address, TRX_TRANSFER_TARGET, sun_amount)
        .memo("TRX Transfer")
        .build()
        .sign(priv_key_obj)
    )
    return txn.broadcast().wait()
