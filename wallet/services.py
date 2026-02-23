import hashlib
import os
import secrets
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from wallet.models import Deposit, MainWallet, Relayer, Sweep, Wallet, WalletServiceSetting

try:
    from tronpy import Tron
    from tronpy.exceptions import AddressNotFound
    from tronpy.keys import PrivateKey
    from tronpy.providers import HTTPProvider
except Exception:  # pragma: no cover
    Tron = None
    HTTPProvider = None
    PrivateKey = None

    class AddressNotFound(Exception):
        pass

try:
    from eth_account import Account
except Exception:  # pragma: no cover
    Account = None

try:
    from web3 import Web3
except Exception:  # pragma: no cover
    Web3 = None


def _env_str(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = str(raw).strip()
    return value or default


DEFAULT_DEPOSIT_NETWORK = Wallet.Network.TRON
TRON_USDT_CONTRACT = _env_str("TRON_USDT_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
BEP20_USDT_CONTRACT = _env_str("BEP20_USDT_CONTRACT", "55d398326f99059fF775485246999027B3197955")
try:
    BEP20_USDT_DECIMALS = int(_env_str("BEP20_USDT_DECIMALS", "18"))
except Exception:
    BEP20_USDT_DECIMALS = 18
TRON_ENDPOINT_URI = _env_str("TRON_ENDPOINT_URI", "https://api.trongrid.io")
TRONGRID_API_KEY = _env_str("TRONGRID_API_KEY", "")
BEP20_RPC_URL = _env_str("BEP20_RPC_URL", "")
FALLBACK_BEP20_RPC_URL = _env_str("FALLBACK_BEP20_RPC_URL", "https://rpc.ankr.com/bsc")
BEP20_RPC_FALLBACK_URLS = [
    item.strip()
    for item in _env_str(
        "BEP20_RPC_FALLBACK_URLS",
        "https://rpc.ankr.com/bsc,"
        "https://bsc-dataseed.binance.org,"
        "https://bsc-dataseed1.binance.org,"
        "https://bsc-dataseed1.defibit.io,"
        "https://rpc.ankr.com/bsc",
    ).split(",")
    if item.strip()
]
try:
    BEP20_AUTOCHECK_LOOKBACK_BLOCKS = int(_env_str("BEP20_AUTOCHECK_LOOKBACK_BLOCKS", "1000"))
except Exception:
    BEP20_AUTOCHECK_LOOKBACK_BLOCKS = 1000
try:
    BEP20_INITIAL_LOOKBACK_BLOCKS = int(_env_str("BEP20_INITIAL_LOOKBACK_BLOCKS", "10000"))
except Exception:
    BEP20_INITIAL_LOOKBACK_BLOCKS = 10000
try:
    BEP20_AUTOCHECK_CHUNK_SIZE = int(_env_str("BEP20_AUTOCHECK_CHUNK_SIZE", "200"))
except Exception:
    BEP20_AUTOCHECK_CHUNK_SIZE = 200
try:
    BEP20_RELAYER_RESERVE_BNB_DEFAULT = Decimal(_env_str("BEP20_RELAYER_RESERVE_BNB", "0.01"))
except Exception:
    BEP20_RELAYER_RESERVE_BNB_DEFAULT = Decimal("0.01")
BSCSCAN_API_URL = _env_str("BSCSCAN_API_URL", "https://api.etherscan.io/v2/api")
BSCSCAN_API_KEY = _env_str("BSCSCAN_API_KEY", "")
BSCSCAN_V2_API_URL = _env_str("BSCSCAN_V2_API_URL", "https://api.etherscan.io/v2/api")
try:
    BEP20_EXPLORER_CHAIN_ID = int(_env_str("BEP20_EXPLORER_CHAIN_ID", "56"))
except Exception:
    BEP20_EXPLORER_CHAIN_ID = 56
_BEP20_DEPOSIT_SOURCE_RAW = _env_str("BEP20_DEPOSIT_SOURCE", "rpc").lower()
BEP20_DEPOSIT_SOURCE = (
    _BEP20_DEPOSIT_SOURCE_RAW
    if _BEP20_DEPOSIT_SOURCE_RAW in {"auto", "rpc", "bscscan"}
    else "auto"
)
try:
    BEP20_BSCSCAN_OFFSET = int(_env_str("BEP20_BSCSCAN_OFFSET", "200"))
except Exception:
    BEP20_BSCSCAN_OFFSET = 200
try:
    BEP20_BSCSCAN_MAX_PAGES = int(_env_str("BEP20_BSCSCAN_MAX_PAGES", "5"))
except Exception:
    BEP20_BSCSCAN_MAX_PAGES = 5


def _split_rpc_urls(value: str) -> list[str]:
    text = str(value or "").replace("\n", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _get_wallet_service_settings() -> WalletServiceSetting | None:
    try:
        return WalletServiceSetting.get_solo()
    except Exception:
        return None


def _get_bep20_runtime_settings() -> dict[str, Any]:
    defaults = {
        "bep20_rpc_url": BEP20_RPC_URL,
        "fallback_bep20_rpc_url": FALLBACK_BEP20_RPC_URL,
        "bep20_rpc_fallback_urls": list(BEP20_RPC_FALLBACK_URLS),
        "autocheck_lookback_blocks": BEP20_AUTOCHECK_LOOKBACK_BLOCKS,
        "initial_lookback_blocks": BEP20_INITIAL_LOOKBACK_BLOCKS,
        "autocheck_chunk_size": BEP20_AUTOCHECK_CHUNK_SIZE,
        "relayer_reserve_bnb": BEP20_RELAYER_RESERVE_BNB_DEFAULT,
        "bscscan_api_url": BSCSCAN_API_URL,
        "bscscan_api_key": BSCSCAN_API_KEY,
        "deposit_source": BEP20_DEPOSIT_SOURCE,
        "bscscan_offset": BEP20_BSCSCAN_OFFSET,
        "bscscan_max_pages": BEP20_BSCSCAN_MAX_PAGES,
    }

    settings = _get_wallet_service_settings()
    if settings is None:
        return defaults

    def _safe_int(value: Any, fallback: int, minimum: int = 1) -> int:
        try:
            parsed = int(value)
        except Exception:
            return fallback
        if parsed < minimum:
            return fallback
        return parsed

    deposit_source = str(settings.bep20_deposit_source or "").strip().lower()
    if deposit_source not in {"auto", "rpc", "bscscan"}:
        deposit_source = defaults["deposit_source"]
    if deposit_source == "auto":
        # Keep behavior predictable: Auto prefers RPC/Ankr path.
        deposit_source = "rpc"

    fallback_urls = _split_rpc_urls(settings.bep20_rpc_fallback_urls or "")
    if not fallback_urls:
        fallback_urls = list(defaults["bep20_rpc_fallback_urls"])

    reserve_bnb = _safe_decimal(settings.bep20_relayer_reserve_bnb, str(defaults["relayer_reserve_bnb"]))
    if reserve_bnb < 0:
        reserve_bnb = defaults["relayer_reserve_bnb"]

    bscscan_api_url = (settings.bscscan_api_url or "").strip() or defaults["bscscan_api_url"]

    return {
        "bep20_rpc_url": (settings.bep20_rpc_url or "").strip(),
        "fallback_bep20_rpc_url": (settings.fallback_bep20_rpc_url or "").strip() or defaults["fallback_bep20_rpc_url"],
        "bep20_rpc_fallback_urls": fallback_urls,
        "autocheck_lookback_blocks": _safe_int(
            settings.bep20_autocheck_lookback_blocks,
            int(defaults["autocheck_lookback_blocks"]),
            1,
        ),
        "initial_lookback_blocks": _safe_int(
            settings.bep20_initial_lookback_blocks,
            int(defaults["initial_lookback_blocks"]),
            1,
        ),
        "autocheck_chunk_size": _safe_int(
            settings.bep20_autocheck_chunk_size,
            int(defaults["autocheck_chunk_size"]),
            1,
        ),
        "relayer_reserve_bnb": reserve_bnb,
        "bscscan_api_url": bscscan_api_url,
        "bscscan_api_key": (settings.bscscan_api_key or "").strip() or defaults["bscscan_api_key"],
        "deposit_source": deposit_source,
        "bscscan_offset": _safe_int(settings.bep20_bscscan_offset, int(defaults["bscscan_offset"]), 1),
        "bscscan_max_pages": _safe_int(settings.bep20_bscscan_max_pages, int(defaults["bscscan_max_pages"]), 1),
    }


def _is_deprecated_v1_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    message = str(payload.get("message") or "").lower()
    result = str(payload.get("result") or "").lower()
    combined = f"{message} {result}"
    return "deprecated v1 endpoint" in combined and "v2" in combined


def _explorer_get_with_v2_fallback(api_url: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    response = requests.get(api_url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if not _is_deprecated_v1_payload(payload):
        return payload, api_url

    v2_url = BSCSCAN_V2_API_URL
    if (api_url or "").strip().rstrip("/") == (v2_url or "").strip().rstrip("/"):
        return payload, api_url

    response = requests.get(v2_url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload, v2_url


NETWORK_META: dict[str, dict[str, Any]] = {
    Wallet.Network.TRON: {
        "label": "TRON (TRC20)",
        "standard": "TRC20",
        "token": "USDT",
        "auto_check_supported": True,
        "sweep_supported": True,
    },
    Wallet.Network.BEP20: {
        "label": "BNB Chain (BEP20)",
        "standard": "BEP20",
        "token": "USDT",
        "auto_check_supported": True,
        "sweep_supported": True,
    },
}

_tron_client = None
_tron_usdt_contract = None
_tron_client_api_key = ""
_bep20_client = None
_bep20_client_rpc_url = ""

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _safe_decimal(value: Any, fallback: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(fallback)


def normalize_network(network: str | None) -> str:
    value = (network or DEFAULT_DEPOSIT_NETWORK).strip().lower()
    if value not in NETWORK_META:
        return DEFAULT_DEPOSIT_NETWORK
    return value


def get_network_meta(network: str | None) -> dict[str, Any]:
    key = normalize_network(network)
    meta = dict(NETWORK_META[key])
    meta["key"] = key
    return meta


def _network_env_prefix(network: str) -> str:
    return "TRON" if network == Wallet.Network.TRON else "BEP20"


def _get_tron_relayer_api_key() -> str:
    try:
        relayer = Relayer.objects.filter(network=Wallet.Network.TRON).only("trongrid_api_key").first()
    except Exception:
        relayer = None
    if relayer is None:
        return ""
    return (relayer.trongrid_api_key or "").strip()


def _get_bep20_bscscan_api_key() -> str:
    runtime_settings = _get_bep20_runtime_settings()
    return str(runtime_settings.get("bscscan_api_key") or "").strip()


def _get_tron_client():
    global _tron_client, _tron_usdt_contract, _tron_client_api_key
    if Tron is None or HTTPProvider is None:
        return None

    api_key = _get_tron_relayer_api_key() or TRONGRID_API_KEY
    if _tron_client is not None and _tron_client_api_key == api_key:
        return _tron_client

    provider_kwargs: dict[str, Any] = {"endpoint_uri": TRON_ENDPOINT_URI}
    if api_key:
        provider_kwargs["api_key"] = api_key
    _tron_client = Tron(provider=HTTPProvider(**provider_kwargs))
    _tron_client_api_key = api_key
    _tron_usdt_contract = None
    return _tron_client


def _get_tron_usdt_contract():
    global _tron_usdt_contract
    client = _get_tron_client()
    if client is None:
        return None
    if _tron_usdt_contract is None:
        _tron_usdt_contract = client.get_contract(TRON_USDT_CONTRACT)
    return _tron_usdt_contract


def _dedupe_rpc_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in urls:
        value = (item or "").strip()
        if not value or value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique


def _get_bep20_rpc_candidates() -> list[str]:
    runtime_settings = _get_bep20_runtime_settings()
    return _dedupe_rpc_urls(
        [
            str(runtime_settings.get("bep20_rpc_url") or "").strip(),
            str(runtime_settings.get("fallback_bep20_rpc_url") or "").strip(),
            *(runtime_settings.get("bep20_rpc_fallback_urls") or []),
        ]
    )


def _get_bep20_client(force_refresh: bool = False, exclude_rpc_urls: list[str] | None = None):
    global _bep20_client, _bep20_client_rpc_url
    if Web3 is None:
        return None

    candidates = _get_bep20_rpc_candidates()
    if exclude_rpc_urls:
        blocked = {(item or "").strip() for item in exclude_rpc_urls if (item or "").strip()}
        candidates = [url for url in candidates if url not in blocked]
    if not candidates:
        _bep20_client = None
        _bep20_client_rpc_url = ""
        return None

    if not force_refresh and _bep20_client is not None and _bep20_client_rpc_url in candidates:
        return _bep20_client

    _bep20_client = None
    _bep20_client_rpc_url = ""
    for rpc_url in candidates:
        try:
            candidate = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
            _ = int(candidate.eth.block_number)
            _bep20_client = candidate
            _bep20_client_rpc_url = rpc_url
            return _bep20_client
        except Exception:
            continue

    return None


def _normalize_hex_key(private_key: str) -> str:
    value = (private_key or "").strip()
    if value.startswith("0x"):
        value = value[2:]
    return value


def _to_checksum_address(client, address: str):
    try:
        return client.to_checksum_address(address)
    except Exception:
        return None


def _topic_address(address: str) -> str:
    clean = (address or "").lower().replace("0x", "")
    return "0x" + ("0" * 24) + clean


def _topic_to_address(topic_value: Any) -> str:
    if hasattr(topic_value, "hex"):
        raw = topic_value.hex()
    else:
        raw = str(topic_value)
    clean = raw.lower().replace("0x", "")
    if len(clean) < 40:
        return ""
    return "0x" + clean[-40:]


def _extract_block_number(raw_payload: dict[str, Any] | None) -> int:
    if not raw_payload:
        return 0
    for key in ("block_number", "blockNumber", "block"):
        value = raw_payload.get(key)
        try:
            if value is not None:
                return int(value)
        except Exception:
            continue
    return 0


def _decode_log_uint256(raw_data: Any) -> int:
    if raw_data is None:
        return 0
    if isinstance(raw_data, int):
        return int(raw_data)
    if isinstance(raw_data, (bytes, bytearray)):
        return int.from_bytes(raw_data, byteorder="big")

    text = raw_data.hex() if hasattr(raw_data, "hex") else str(raw_data)
    text = text.strip()
    if not text:
        return 0
    if not text.startswith("0x"):
        text = f"0x{text}"
    try:
        return int(text, 16)
    except Exception:
        return 0


def _calculate_affordable_native_transfer_wei(
    sender_balance_wei: int,
    gas_price_wei: int,
    gas_limit: int,
    requested_value_wei: int,
    reserve_wei: int = 0,
) -> int:
    balance = max(int(sender_balance_wei or 0), 0)
    gas_price = max(int(gas_price_wei or 0), 0)
    limit = max(int(gas_limit or 0), 0)
    requested = max(int(requested_value_wei or 0), 0)
    reserve = max(int(reserve_wei or 0), 0)
    if requested <= 0:
        return 0

    spendable = balance - (gas_price * limit) - reserve
    if spendable <= 0:
        return 0

    return min(spendable, requested)


def _generate_fallback_address(network: str) -> tuple[str, str]:
    private_key = secrets.token_hex(32)
    digest = hashlib.sha256(private_key.encode("utf-8")).hexdigest()
    if network == Wallet.Network.TRON:
        return f"T{digest[:33]}", private_key
    return f"0x{digest[:40]}", private_key


def _generate_wallet_credentials(network: str) -> dict[str, str]:
    if network == Wallet.Network.TRON:
        client = _get_tron_client()
        if client is not None:
            try:
                account = client.generate_address()
                return {
                    "address": account["base58check_address"],
                    "private_key": account["private_key"],
                }
            except Exception:
                pass
    elif network == Wallet.Network.BEP20 and Account is not None:
        try:
            account = Account.create()
            return {
                "address": account.address,
                "private_key": account.key.hex(),
            }
        except Exception:
            pass

    address, private_key = _generate_fallback_address(network)
    return {"address": address, "private_key": private_key}


def get_or_create_user_profile(user: User):
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@transaction.atomic
def ensure_user_network_wallet(user: User, network: str) -> tuple[Wallet, bool]:
    selected_network = normalize_network(network)
    profile = get_or_create_user_profile(user)

    wallet = Wallet.objects.filter(user=user, network=selected_network).first()
    if wallet:
        if wallet.profile_id != profile.id:
            wallet.profile = profile
            wallet.save(update_fields=["profile", "updated_at"])
        return wallet, False

    credentials = _generate_wallet_credentials(selected_network)
    wallet = Wallet.objects.create(
        user=user,
        profile=profile,
        network=selected_network,
        address=credentials["address"],
        private_key=credentials["private_key"],
    )
    return wallet, True


@transaction.atomic
def ensure_user_wallets(user: User) -> dict[str, Any]:
    created = []
    wallets = []
    for network in NETWORK_META:
        wallet, was_created = ensure_user_network_wallet(user, network)
        wallets.append(wallet)
        if was_created:
            created.append(wallet)
    return {"wallets": wallets, "created": created}


def ensure_all_users_wallets() -> dict[str, int]:
    created_count = 0
    scanned_users = 0
    for user in User.objects.all().only("id"):
        scanned_users += 1
        result = ensure_user_wallets(user)
        created_count += len(result["created"])
    return {"users": scanned_users, "created_wallets": created_count}


def get_user_wallet(user: User, network: str) -> Wallet | None:
    selected_network = normalize_network(network)
    return Wallet.objects.filter(user=user, network=selected_network).first()


def get_or_create_relayer(network: str) -> Relayer:
    selected_network = normalize_network(network)
    prefix = _network_env_prefix(selected_network)
    runtime_settings = _get_bep20_runtime_settings()
    default_rpc_url = str(runtime_settings.get("bep20_rpc_url") or "") if selected_network == Wallet.Network.BEP20 else ""
    default_bscscan_api_key = (
        str(runtime_settings.get("bscscan_api_key") or "")
        if selected_network == Wallet.Network.BEP20
        else ""
    )
    default_trongrid_api_key = TRONGRID_API_KEY if selected_network == Wallet.Network.TRON else ""
    default_reserve_native = (
        _safe_decimal(runtime_settings.get("relayer_reserve_bnb"), str(BEP20_RELAYER_RESERVE_BNB_DEFAULT))
        if selected_network == Wallet.Network.BEP20
        else Decimal("0")
    )
    relayer, _ = Relayer.objects.get_or_create(
        network=selected_network,
        defaults={
            "address": os.getenv(f"{prefix}_RELAYER_ADDRESS", "").strip(),
            "private_key": os.getenv(f"{prefix}_RELAYER_PRIVATE_KEY", "").strip(),
            "rpc_url": default_rpc_url,
            "bscscan_api_key": default_bscscan_api_key,
            "trongrid_api_key": default_trongrid_api_key,
            "min_native_balance": _safe_decimal(os.getenv(f"{prefix}_RELAYER_MIN_NATIVE", "1"), "1"),
            "topup_amount": _safe_decimal(os.getenv(f"{prefix}_RELAYER_TOPUP_AMOUNT", "3"), "3"),
            "reserve_native_balance": _safe_decimal(
                os.getenv(f"{prefix}_RELAYER_RESERVE_NATIVE", str(default_reserve_native)),
                str(default_reserve_native),
            ),
        },
    )
    return relayer


def get_or_create_main_wallet(network: str) -> MainWallet:
    selected_network = normalize_network(network)
    prefix = _network_env_prefix(selected_network)
    main_wallet, _ = MainWallet.objects.get_or_create(
        network=selected_network,
        defaults={
            "address": os.getenv(f"{prefix}_MAIN_ADDRESS", "").strip(),
            "private_key": os.getenv(f"{prefix}_MAIN_PRIVATE_KEY", "").strip(),
        },
    )
    return main_wallet


def relayer_is_configured(network: str) -> bool:
    relayer = get_or_create_relayer(network)
    return relayer.is_configured


def main_wallet_is_configured(network: str) -> bool:
    main_wallet = get_or_create_main_wallet(network)
    return main_wallet.is_configured


def get_deposit_address(user: User, network: str) -> str:
    wallet, _ = ensure_user_network_wallet(user, normalize_network(network))
    return wallet.address


def get_supported_networks(user: User) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for network in NETWORK_META:
        wallet, _ = ensure_user_network_wallet(user, network)
        meta = get_network_meta(network)
        meta["available"] = bool(wallet.address)
        meta["address"] = wallet.address
        meta["relayer_available"] = relayer_is_configured(network)
        meta["main_wallet_available"] = main_wallet_is_configured(network)
        options.append(meta)
    return options


def build_qr_payload(network: str, address: str) -> str:
    return (address or "").strip()


def _credit_internal_balances(wallet: Wallet, amount: Decimal):
    wallet.balance += amount
    wallet.total_balance += amount
    wallet.save(update_fields=["balance", "total_balance", "updated_at"])

    profile = wallet.profile
    profile.balance += amount
    profile.save(update_fields=["balance"])


def _create_confirmed_deposit(
    wallet: Wallet,
    amount: Decimal,
    txid: str,
    payload: dict[str, Any] | None = None,
) -> tuple[Deposit, bool]:
    deposit, created = Deposit.objects.get_or_create(
        txid=txid,
        defaults={
            "wallet": wallet,
            "network": wallet.network,
            "amount": amount,
            "status": Deposit.Status.CONFIRMED,
            "confirmed_at": timezone.now(),
            "raw_payload": payload or {},
        },
    )
    if created:
        _credit_internal_balances(wallet, amount)
    return deposit, created


def check_wallet_deposits(wallet: Wallet) -> dict[str, Any]:
    if wallet.network == Wallet.Network.TRON:
        return _check_tron_deposits(wallet)
    if wallet.network == Wallet.Network.BEP20:
        return _check_bep20_deposits(wallet)
    return {"ok": False, "created": 0, "processed": 0, "created_amount": Decimal("0"), "message": "Unsupported network."}


def _check_tron_deposits(wallet: Wallet) -> dict[str, Any]:
    result = {"ok": True, "created": 0, "processed": 0, "created_amount": Decimal("0"), "message": ""}
    try:
        url = f"{TRON_ENDPOINT_URI}/v1/accounts/{wallet.address}/transactions/trc20"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        result["ok"] = False
        result["message"] = f"Failed to fetch TRON deposits: {exc}"
        return result

    for tx in payload.get("data", []):
        result["processed"] += 1
        to_address = tx.get("to")
        token_address = ((tx.get("token_info") or {}).get("address") or "").lower()
        txid = tx.get("transaction_id")
        if to_address != wallet.address or not txid:
            continue
        if token_address != TRON_USDT_CONTRACT.lower():
            continue

        amount = _safe_decimal(tx.get("value", "0")) / Decimal("1000000")
        if amount <= 0:
            continue

        _, created = _create_confirmed_deposit(wallet, amount, txid, payload=tx)
        if created:
            _record_created_deposit(result, amount)

    _set_deposit_result_message(result)
    return result


def _format_deposit_amount(amount: Any) -> str:
    value = _safe_decimal(amount)
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _record_created_deposit(result: dict[str, Any], amount: Any):
    result["created"] = int(result.get("created", 0) or 0) + 1
    result["created_amount"] = _safe_decimal(result.get("created_amount", "0")) + _safe_decimal(amount)


def _set_deposit_result_message(result: dict[str, Any]):
    created_count = int(result.get("created", 0) or 0)
    if created_count <= 0:
        result["message"] = "No new deposits found."
        return

    total_amount = _format_deposit_amount(result.get("created_amount", "0"))
    if created_count == 1:
        result["message"] = f"Deposit received: {total_amount} USDT credited to your balance."
        return

    result["message"] = (
        f"Deposits received: {created_count} transactions, "
        f"total {total_amount} USDT credited to your balance."
    )


def _resolve_bep20_scan_start_block(
    latest_block: int,
    last_confirmed_block: int,
    last_scanned_block: int,
) -> int:
    latest = max(int(latest_block or 0), 0)
    confirmed = max(int(last_confirmed_block or 0), 0)
    scanned = max(int(last_scanned_block or 0), 0)
    cursor = max(confirmed, scanned)
    if cursor > 0:
        return cursor + 1

    runtime_settings = _get_bep20_runtime_settings()
    initial_lookback = max(
        int(runtime_settings.get("initial_lookback_blocks") or 1),
        int(runtime_settings.get("autocheck_lookback_blocks") or 1),
        1,
    )
    return max(0, latest - initial_lookback + 1)


def _update_wallet_last_scanned_block(wallet: Wallet, block_number: int):
    target = max(int(block_number or 0), 0)
    current = max(int(getattr(wallet, "last_scanned_block", 0) or 0), 0)
    if target <= current:
        return
    wallet.last_scanned_block = target
    wallet.save(update_fields=["last_scanned_block", "updated_at"])


def _decode_hex_message(raw_value: Any) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""

    clean = text[2:] if text.lower().startswith("0x") else text
    if clean and len(clean) % 2 == 0:
        try:
            decoded = bytes.fromhex(clean).decode("utf-8", errors="ignore").strip()
            if decoded:
                return decoded
        except Exception:
            pass
    return text


def _tron_tx_error_message(tx_result: Any) -> str:
    if not isinstance(tx_result, dict):
        return ""

    receipt = tx_result.get("receipt") or {}
    receipt_result = str(receipt.get("result") or "").strip().upper()
    tx_result_value = str(tx_result.get("result") or "").strip().upper()
    contract_ret = str(tx_result.get("contractRet") or "").strip().upper()

    if receipt_result and receipt_result not in {"SUCCESS"}:
        reason = receipt_result
    elif tx_result_value and tx_result_value not in {"SUCCESS", "TRUE"}:
        reason = tx_result_value
    elif contract_ret and contract_ret not in {"SUCCESS"}:
        reason = contract_ret
    else:
        return ""

    detail = _decode_hex_message(tx_result.get("resMessage"))
    return f"{reason}: {detail}" if detail else reason


def _get_last_confirmed_bep20_block(wallet: Wallet) -> int:
    last_dep = (
        wallet.deposits.filter(network=Wallet.Network.BEP20, status=Deposit.Status.CONFIRMED)
        .exclude(raw_payload=None)
        .order_by("-created_at")
        .first()
    )
    return _extract_block_number(last_dep.raw_payload if last_dep else None)


def _get_bep20_latest_block_via_bscscan() -> int:
    runtime_settings = _get_bep20_runtime_settings()
    bscscan_api_url = str(runtime_settings.get("bscscan_api_url") or "").strip() or BSCSCAN_API_URL
    params: dict[str, Any] = {
        "chainid": str(BEP20_EXPLORER_CHAIN_ID),
        "module": "proxy",
        "action": "eth_blockNumber",
    }
    bscscan_api_key = _get_bep20_bscscan_api_key()
    if bscscan_api_key:
        params["apikey"] = bscscan_api_key

    try:
        payload, _ = _explorer_get_with_v2_fallback(bscscan_api_url, params)
    except Exception:
        return 0

    raw_block = payload.get("result")
    if raw_block is None:
        return 0

    text = str(raw_block).strip()
    if not text:
        return 0

    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text)
    except Exception:
        return 0


def _resolve_bep20_bscscan_start_block(last_confirmed_block: int, last_scanned_block: int) -> tuple[int, int]:
    confirmed = max(int(last_confirmed_block or 0), 0)
    scanned = max(int(last_scanned_block or 0), 0)
    cursor = max(confirmed, scanned)
    latest = max(_get_bep20_latest_block_via_bscscan(), 0)
    if cursor > 0:
        return cursor + 1, latest

    if latest > 0:
        runtime_settings = _get_bep20_runtime_settings()
        initial_lookback = max(
            int(runtime_settings.get("initial_lookback_blocks") or 1),
            int(runtime_settings.get("autocheck_lookback_blocks") or 1),
            1,
        )
        return max(0, latest - initial_lookback + 1), latest

    return 0, 0


def _check_bep20_deposits_via_bscscan(
    wallet: Wallet,
    start_block: int = 0,
    end_block: int | None = None,
) -> dict[str, Any]:
    result = {"ok": True, "created": 0, "processed": 0, "created_amount": Decimal("0"), "message": ""}
    address = (wallet.address or "").strip()
    if not address:
        result["ok"] = False
        result["message"] = "Wallet address is missing."
        return result

    if not BEP20_USDT_CONTRACT:
        result["ok"] = False
        result["message"] = "BEP20 USDT contract is not configured."
        return result

    runtime_settings = _get_bep20_runtime_settings()
    bscscan_api_url = str(runtime_settings.get("bscscan_api_url") or "").strip() or BSCSCAN_API_URL
    offset = max(int(runtime_settings.get("bscscan_offset") or 1), 50)
    max_pages = max(int(runtime_settings.get("bscscan_max_pages") or 1), 1)
    normalized_address = address.lower()
    bscscan_api_key = _get_bep20_bscscan_api_key()
    page = 1
    while page <= max_pages:
        params: dict[str, Any] = {
            "chainid": str(BEP20_EXPLORER_CHAIN_ID),
            "module": "account",
            "action": "tokentx",
            "address": address,
            "contractaddress": BEP20_USDT_CONTRACT,
            "startblock": max(int(start_block or 0), 0),
            "endblock": int(end_block) if end_block is not None else 99_999_999,
            "page": page,
            "offset": offset,
            "sort": "asc",
        }
        if bscscan_api_key:
            params["apikey"] = bscscan_api_key

        try:
            payload, used_api_url = _explorer_get_with_v2_fallback(bscscan_api_url, params)
            bscscan_api_url = used_api_url
        except Exception as exc:
            result["ok"] = False
            result["message"] = f"BscScan fallback failed: {exc}"
            return result

        status = str(payload.get("status", "")).strip()
        raw_result = payload.get("result")
        if status == "0":
            text = str(raw_result or payload.get("message") or "").strip()
            lowered = text.lower()
            if "deprecated v1 endpoint" in lowered:
                result["ok"] = False
                result["message"] = (
                    "Explorer V1 endpoint is deprecated. "
                    "Set BSCSCAN_API_URL to https://api.etherscan.io/v2/api and use an Etherscan API key."
                )
                return result
            if "no transactions found" in lowered:
                _set_deposit_result_message(result)
                return result
            if "rate limit" in lowered:
                result["ok"] = False
                result["message"] = "BscScan rate limit reached. Please add BSCSCAN_API_KEY."
                return result
            if "api key" in lowered:
                result["ok"] = False
                result["message"] = "BscScan API key is invalid or missing."
                return result
            result["ok"] = False
            result["message"] = f"BscScan fallback error: {text or 'unknown error'}"
            return result

        if not isinstance(raw_result, list):
            result["ok"] = False
            result["message"] = "BscScan fallback returned invalid payload."
            return result
        if not raw_result:
            break

        for tx in raw_result:
            result["processed"] += 1
            to_address = str(tx.get("to") or "").lower()
            if to_address != normalized_address:
                continue

            txid = str(tx.get("hash") or "").strip()
            if not txid:
                continue

            try:
                confirmations = int(str(tx.get("confirmations", "0")).strip())
            except Exception:
                confirmations = 0
            if confirmations <= 0:
                continue

            token_decimals = BEP20_USDT_DECIMALS
            try:
                token_decimals = int(str(tx.get("tokenDecimal", BEP20_USDT_DECIMALS)).strip())
            except Exception:
                token_decimals = BEP20_USDT_DECIMALS

            decimals_factor = Decimal(10) ** Decimal(max(token_decimals, 0))
            amount = _safe_decimal(tx.get("value", "0")) / decimals_factor
            if amount <= 0:
                continue

            try:
                block_number = int(str(tx.get("blockNumber", "0")).strip())
            except Exception:
                block_number = 0
            try:
                log_index = int(str(tx.get("transactionIndex", "0")).strip())
            except Exception:
                log_index = 0

            row_payload = {
                "source": "bscscan",
                "block_number": block_number,
                "log_index": log_index,
                "transaction_hash": txid,
                "from": str(tx.get("from") or ""),
                "to": str(tx.get("to") or ""),
            }

            _, created = _create_confirmed_deposit(wallet, amount, txid, payload=row_payload)
            if created:
                _record_created_deposit(result, amount)

        if len(raw_result) < offset:
            break
        page += 1

    _set_deposit_result_message(result)
    return result


def _run_bep20_deposits_via_bscscan(
    wallet: Wallet,
    start_block: int = 0,
    end_block: int | None = None,
) -> dict[str, Any]:
    result = _check_bep20_deposits_via_bscscan(wallet, start_block=start_block, end_block=end_block)
    if not result.get("ok"):
        return result

    latest_block = 0
    if end_block is not None:
        latest_block = max(int(end_block or 0), 0)
    else:
        latest_block = max(_get_bep20_latest_block_via_bscscan(), 0)

    if latest_block > 0:
        _update_wallet_last_scanned_block(wallet, latest_block)

    return result


def _check_bep20_deposits(wallet: Wallet) -> dict[str, Any]:
    result = {"ok": True, "created": 0, "processed": 0, "created_amount": Decimal("0"), "message": ""}
    last_processed_block = _get_last_confirmed_bep20_block(wallet)
    last_scanned_block = max(int(getattr(wallet, "last_scanned_block", 0) or 0), 0)
    runtime_settings = _get_bep20_runtime_settings()
    scan_source = str(runtime_settings.get("deposit_source") or "auto").strip().lower()

    if scan_source == "bscscan":
        fallback_start, fallback_latest = _resolve_bep20_bscscan_start_block(
            last_confirmed_block=last_processed_block,
            last_scanned_block=last_scanned_block,
        )
        fallback_end = fallback_latest if fallback_latest > 0 else None
        return _run_bep20_deposits_via_bscscan(wallet, start_block=fallback_start, end_block=fallback_end)

    client = _get_bep20_client()
    if client is None:
        if scan_source == "rpc":
            result["ok"] = False
            result["message"] = "BEP20 RPC is unavailable. Configure BEP20_RPC_URL in environment."
            return result

        fallback_start, fallback_latest = _resolve_bep20_bscscan_start_block(
            last_confirmed_block=last_processed_block,
            last_scanned_block=last_scanned_block,
        )
        fallback_end = fallback_latest if fallback_latest > 0 else None
        return _run_bep20_deposits_via_bscscan(wallet, start_block=fallback_start, end_block=fallback_end)

    token_address = _to_checksum_address(client, BEP20_USDT_CONTRACT)
    wallet_address = _to_checksum_address(client, wallet.address)
    if not token_address or not wallet_address:
        result["ok"] = False
        result["message"] = "BEP20 contract or wallet address is invalid."
        return result

    try:
        latest_block = int(client.eth.block_number)
    except Exception as exc:
        if scan_source == "rpc":
            result["ok"] = False
            result["message"] = f"Failed to read latest BEP20 block: {exc}"
            return result

        fallback_start, fallback_latest = _resolve_bep20_bscscan_start_block(
            last_confirmed_block=last_processed_block,
            last_scanned_block=last_scanned_block,
        )
        fallback_end = fallback_latest if fallback_latest > 0 else None
        fallback = _run_bep20_deposits_via_bscscan(wallet, start_block=fallback_start, end_block=fallback_end)
        if fallback.get("ok"):
            return fallback
        result["ok"] = False
        result["message"] = f"Failed to read latest BEP20 block: {exc}. Fallback failed: {fallback.get('message', '')}"
        return result

    start_block = _resolve_bep20_scan_start_block(
        latest_block=latest_block,
        last_confirmed_block=last_processed_block,
        last_scanned_block=last_scanned_block,
    )

    if start_block > latest_block:
        result["message"] = "No new deposits found."
        _update_wallet_last_scanned_block(wallet, latest_block)
        return result

    chunk_size = max(int(runtime_settings.get("autocheck_chunk_size") or 1), 1)
    min_chunk_size = 1 if scan_source == "rpc" else 50
    transfer_topic = client.keccak(text="Transfer(address,address,uint256)").hex()
    to_topic = _topic_address(wallet_address)

    current_from = start_block
    while current_from <= latest_block:
        current_chunk = chunk_size
        logs = None
        current_to = min(current_from + current_chunk - 1, latest_block)
        while logs is None:
            current_to = min(current_from + current_chunk - 1, latest_block)
            try:
                logs = client.eth.get_logs(
                    {
                        "fromBlock": current_from,
                        "toBlock": current_to,
                        "address": token_address,
                        "topics": [transfer_topic, None, to_topic],
                    }
                )
            except Exception as exc:
                error_text = str(exc).lower()
                if ("limit exceeded" in error_text or "-32005" in error_text) and current_chunk > min_chunk_size:
                    current_chunk = max(min_chunk_size, current_chunk // 2)
                    continue
                if ("limit exceeded" in error_text or "-32005" in error_text) and scan_source != "rpc":
                    fallback = _run_bep20_deposits_via_bscscan(
                        wallet,
                        start_block=current_from,
                        end_block=latest_block,
                    )
                    if fallback.get("ok"):
                        result["created"] += int(fallback.get("created", 0) or 0)
                        result["processed"] += int(fallback.get("processed", 0) or 0)
                        result["created_amount"] = (
                            _safe_decimal(result.get("created_amount", "0"))
                            + _safe_decimal(fallback.get("created_amount", "0"))
                        )
                        _set_deposit_result_message(result)
                        return result
                    result["ok"] = False
                    result["message"] = (
                        f"Failed to scan BEP20 logs and BscScan fallback: {fallback.get('message', 'unknown error')}"
                    )
                    return result
                if "limit exceeded" in error_text or "-32005" in error_text:
                    if scan_source == "rpc":
                        previous_rpc_url = str(_bep20_client_rpc_url or "").strip()
                        switched_client = _get_bep20_client(
                            force_refresh=True,
                            exclude_rpc_urls=[previous_rpc_url] if previous_rpc_url else None,
                        )
                        switched_rpc_url = str(_bep20_client_rpc_url or "").strip()
                        if switched_client is not None and switched_rpc_url and switched_rpc_url != previous_rpc_url:
                            client = switched_client
                            token_address = _to_checksum_address(client, BEP20_USDT_CONTRACT)
                            wallet_address = _to_checksum_address(client, wallet.address)
                            if not token_address or not wallet_address:
                                result["ok"] = False
                                result["message"] = "BEP20 contract or wallet address is invalid."
                                return result
                            transfer_topic = client.keccak(text="Transfer(address,address,uint256)").hex()
                            to_topic = _topic_address(wallet_address)
                            continue

                    result["ok"] = False
                    result["message"] = (
                        f"BEP20 RPC returned range/limit error at chunk={current_chunk}. "
                        "Reduce chunk size or use another RPC endpoint."
                    )
                    return result
                result["ok"] = False
                result["message"] = f"Failed to scan BEP20 logs: {exc}"
                return result

        for log in logs:
            result["processed"] += 1
            tx_hash_value = log.get("transactionHash")
            txid = tx_hash_value.hex() if hasattr(tx_hash_value, "hex") else str(tx_hash_value or "")
            if not txid:
                continue

            raw_amount = _decode_log_uint256(log.get("data"))
            if raw_amount <= 0:
                continue

            decimals_factor = Decimal(10) ** Decimal(max(BEP20_USDT_DECIMALS, 0))
            amount = _safe_decimal(raw_amount) / decimals_factor
            if amount <= 0:
                continue

            topics = log.get("topics") or []
            from_address = _topic_to_address(topics[1]) if len(topics) > 1 else ""
            to_address = _topic_to_address(topics[2]) if len(topics) > 2 else wallet_address

            payload = {
                "block_number": int(log.get("blockNumber", 0) or 0),
                "log_index": int(log.get("logIndex", 0) or 0),
                "transaction_hash": txid,
                "from": from_address,
                "to": to_address,
            }

            _, created = _create_confirmed_deposit(wallet, amount, txid, payload=payload)
            if created:
                _record_created_deposit(result, amount)

        current_from = current_to + 1

    _set_deposit_result_message(result)
    _update_wallet_last_scanned_block(wallet, latest_block)
    return result


def webhook_deposit(network: str, to_address: str, txid: str, amount: Decimal, payload: dict[str, Any] | None = None):
    selected_network = normalize_network(network)
    wallet = Wallet.objects.filter(network=selected_network, address=to_address).first()
    if wallet is None:
        return {"ok": False, "message": "Wallet not found."}
    if amount <= 0:
        return {"ok": False, "message": "Amount must be greater than zero."}

    _, created = _create_confirmed_deposit(wallet, amount, txid, payload=payload)
    return {"ok": True, "created": created}


def _tron_private_key(private_key: str):
    if PrivateKey is None:
        return None
    value = (private_key or "").strip()
    if value.startswith("0x"):
        value = value[2:]
    try:
        return PrivateKey(bytes.fromhex(value))
    except Exception:
        return None


def _get_trx_balance(address: str) -> Decimal | None:
    client = _get_tron_client()
    if client is None:
        return None
    try:
        return _safe_decimal(client.get_account_balance(address))
    except AddressNotFound:
        return Decimal("0")
    except Exception:
        return None


def _get_bep20_native_balance(address: str) -> Decimal | None:
    client = _get_bep20_client()
    if client is None:
        return None
    checksum = _to_checksum_address(client, address)
    if not checksum:
        return None
    try:
        wei_value = client.eth.get_balance(checksum)
    except Exception:
        return None
    return _safe_decimal(wei_value) / Decimal("1000000000000000000")


def topup_wallet_gas(wallet: Wallet) -> dict[str, Any]:
    if wallet.network == Wallet.Network.TRON:
        return _topup_tron_gas(wallet)
    if wallet.network == Wallet.Network.BEP20:
        return _topup_bep20_gas(wallet)
    return {"ok": False, "message": "Unsupported network."}


def _topup_tron_gas(wallet: Wallet) -> dict[str, Any]:
    client = _get_tron_client()
    if client is None:
        return {"ok": False, "message": "TRON client is unavailable on this server."}

    relayer = get_or_create_relayer(Wallet.Network.TRON)
    if not relayer.is_configured:
        return {"ok": False, "message": "TRON relayer is not configured."}

    relayer_key = _tron_private_key(relayer.private_key)
    if relayer_key is None:
        return {"ok": False, "message": "TRON relayer private key is invalid."}

    current_balance = _get_trx_balance(wallet.address)
    if current_balance is None:
        return {"ok": False, "message": "Failed to check wallet TRX balance."}
    if current_balance >= relayer.min_native_balance:
        return {
            "ok": True,
            "topped_up": False,
            "message": "Gas balance is already sufficient.",
            "balance": str(current_balance),
        }

    topup_sun = int(_safe_decimal(relayer.topup_amount) * Decimal("1000000"))
    if topup_sun <= 0:
        return {"ok": False, "message": "Invalid relayer top-up amount."}

    try:
        tx = (
            client.trx.transfer(relayer.address, wallet.address, topup_sun)
            .memo("Site relayer gas top-up")
            .build()
            .sign(relayer_key)
        )
        tx_result = tx.broadcast().wait()
        txid = tx_result.get("id") if isinstance(tx_result, dict) else ""
    except Exception as exc:
        return {"ok": False, "message": f"TRON gas top-up failed: {exc}"}

    tx_error = _tron_tx_error_message(tx_result)
    if tx_error:
        return {"ok": False, "message": f"TRON gas top-up failed on-chain: {tx_error}"}

    return {
        "ok": True,
        "topped_up": True,
        "txid": txid,
        "message": f"Relayer sent {relayer.topup_amount} TRX for gas.",
    }


def _topup_bep20_gas(wallet: Wallet) -> dict[str, Any]:
    client = _get_bep20_client()
    if client is None:
        return {
            "ok": False,
            "message": "BEP20 RPC is unavailable. Configure BEP20_RPC_URL in environment.",
        }
    if Account is None:
        return {"ok": False, "message": "eth-account is unavailable."}

    relayer = get_or_create_relayer(Wallet.Network.BEP20)
    if not relayer.is_configured:
        return {"ok": False, "message": "BEP20 relayer is not configured."}

    current_balance = _get_bep20_native_balance(wallet.address)
    if current_balance is None:
        return {"ok": False, "message": "Failed to check wallet BNB balance."}
    if current_balance >= relayer.min_native_balance:
        return {
            "ok": True,
            "topped_up": False,
            "message": "Gas balance is already sufficient.",
            "balance": str(current_balance),
        }

    relayer_key = _normalize_hex_key(relayer.private_key)
    try:
        relayer_account = Account.from_key(relayer_key)
    except Exception:
        return {"ok": False, "message": "BEP20 relayer private key is invalid."}

    relayer_address = _to_checksum_address(client, relayer_account.address)
    target_address = _to_checksum_address(client, wallet.address)
    if not relayer_address or not target_address:
        return {"ok": False, "message": "Relayer or wallet address is invalid."}

    requested_value_wei = int(_safe_decimal(relayer.topup_amount) * Decimal("1000000000000000000"))
    if requested_value_wei <= 0:
        return {"ok": False, "message": "Invalid relayer top-up amount."}
    min_target_balance_wei = int(_safe_decimal(relayer.min_native_balance) * Decimal("1000000000000000000"))
    current_target_balance_wei = int(current_balance * Decimal("1000000000000000000"))
    needed_value_wei = max(min_target_balance_wei - current_target_balance_wei, 0)
    if needed_value_wei > 0:
        requested_value_wei = min(requested_value_wei, needed_value_wei)

    try:
        nonce = client.eth.get_transaction_count(relayer_address)
        gas_price = int(client.eth.gas_price)
        relayer_balance_wei = int(client.eth.get_balance(relayer_address))
        gas_limit = 21000
        runtime_settings = _get_bep20_runtime_settings()
        reserve_default = _safe_decimal(
            runtime_settings.get("relayer_reserve_bnb"),
            str(BEP20_RELAYER_RESERVE_BNB_DEFAULT),
        )
        reserve_native_balance = _safe_decimal(reserve_default, str(BEP20_RELAYER_RESERVE_BNB_DEFAULT))
        reserve_wei = int(max(reserve_native_balance, Decimal("0")) * Decimal("1000000000000000000"))
        value_wei = _calculate_affordable_native_transfer_wei(
            sender_balance_wei=relayer_balance_wei,
            gas_price_wei=gas_price,
            gas_limit=gas_limit,
            requested_value_wei=requested_value_wei,
            reserve_wei=reserve_wei,
        )
        if value_wei <= 0:
            needed_fee_wei = gas_limit * gas_price
            return {
                "ok": False,
                "message": (
                    "BEP20 relayer balance is too low for gas top-up transaction fee. "
                    f"Balance={_safe_decimal(relayer_balance_wei) / Decimal('1000000000000000000')} BNB, "
                    f"Required fee~{_safe_decimal(needed_fee_wei) / Decimal('1000000000000000000')} BNB, "
                    f"Reserve={reserve_native_balance} BNB."
                ),
            }
        tx = {
            "chainId": client.eth.chain_id,
            "nonce": nonce,
            "to": target_address,
            "value": value_wei,
            "gas": gas_limit,
            "gasPrice": gas_price,
        }
        signed = client.eth.account.sign_transaction(tx, private_key=relayer_key)
        raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        tx_hash = client.eth.send_raw_transaction(raw_tx)
        receipt = client.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    except Exception as exc:
        return {"ok": False, "message": f"BEP20 gas top-up failed: {exc}"}

    if int(receipt.status) != 1:
        return {"ok": False, "message": "BEP20 gas top-up failed on-chain."}

    txid = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    sent_amount = _safe_decimal(value_wei) / Decimal("1000000000000000000")
    requested_amount = _safe_decimal(requested_value_wei) / Decimal("1000000000000000000")
    partial = value_wei < requested_value_wei
    return {
        "ok": True,
        "topped_up": True,
        "txid": txid,
        "partial": partial,
        "message": (
            f"Relayer sent {sent_amount} BNB for gas."
            if not partial
            else (
                "Relayer balance is below configured top-up amount. "
                f"Sent {sent_amount} BNB instead of {requested_amount} BNB "
                f"while keeping {reserve_native_balance} BNB reserve."
            )
        ),
    }


def sweep_wallet_to_main(wallet: Wallet) -> dict[str, Any]:
    amount = _safe_decimal(wallet.balance)

    main_wallet = get_or_create_main_wallet(wallet.network)
    if not main_wallet.is_configured:
        return {"ok": False, "message": "Main wallet is not configured for this network."}

    sweep = Sweep.objects.create(
        wallet=wallet,
        network=wallet.network,
        amount=amount,
        destination_address=main_wallet.address,
        status=Sweep.Status.PENDING,
        fee_payer=Sweep.FeePayer.RELAYER,
    )

    gas_result = topup_wallet_gas(wallet)
    if not gas_result.get("ok"):
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = gas_result.get("message", "Gas top-up failed.")
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    if wallet.network == Wallet.Network.TRON:
        return _sweep_tron(wallet, main_wallet, sweep)
    if wallet.network == Wallet.Network.BEP20:
        return _sweep_bep20(wallet, main_wallet, sweep)

    sweep.status = Sweep.Status.FAILED
    sweep.error_message = "Sweep is not enabled for this network."
    sweep.completed_at = timezone.now()
    sweep.save(update_fields=["status", "error_message", "completed_at"])
    return {"ok": False, "message": sweep.error_message, "sweep": sweep}


def _sweep_tron(wallet: Wallet, main_wallet: MainWallet, sweep: Sweep) -> dict[str, Any]:
    client = _get_tron_client()
    contract = _get_tron_usdt_contract()
    if client is None or contract is None:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "TRON client/contract is unavailable."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    owner_key = _tron_private_key(wallet.private_key)
    if owner_key is None:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "Wallet private key is invalid."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    trx_balance = _get_trx_balance(wallet.address)
    if trx_balance is None or trx_balance <= 0:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "TRX balance is insufficient for fees."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    try:
        raw_balance = contract.functions.balanceOf(wallet.address)
        if int(raw_balance) <= 0:
            sweep.status = Sweep.Status.FAILED
            sweep.error_message = "No on-chain USDT balance to transfer."
            sweep.completed_at = timezone.now()
            sweep.save(update_fields=["status", "error_message", "completed_at"])
            return {"ok": False, "message": sweep.error_message, "sweep": sweep}

        tx = (
            contract.functions.transfer(main_wallet.address, int(raw_balance))
            .with_owner(wallet.address)
            .fee_limit(20_000_000)
            .build()
            .sign(owner_key)
        )
        tx_result = tx.broadcast().wait()
        txid = tx_result.get("id") if isinstance(tx_result, dict) else ""
    except Exception as exc:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = f"Sweep transaction failed: {exc}"
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    tx_error = _tron_tx_error_message(tx_result)
    if tx_error:
        sweep.status = Sweep.Status.FAILED
        if "OUT_OF_ENERGY" in tx_error.upper():
            sweep.error_message = (
                "Sweep transaction failed on-chain: OUT_OF_ENERGY. "
                "Increase TRON relayer top-up/min native balance and try again."
            )
        else:
            sweep.error_message = f"Sweep transaction failed on-chain: {tx_error}"
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    transferred_amount = _safe_decimal(raw_balance) / Decimal("1000000")
    wallet.balance = Decimal("0")
    wallet.save(update_fields=["balance", "updated_at"])

    sweep.status = Sweep.Status.SUCCESS
    sweep.txid = txid
    sweep.amount = transferred_amount
    sweep.completed_at = timezone.now()
    sweep.save(update_fields=["status", "txid", "amount", "completed_at"])

    return {
        "ok": True,
        "message": f"Swept {transferred_amount} USDT to main wallet: {main_wallet.address}.",
        "sweep": sweep,
    }


def _sweep_bep20(wallet: Wallet, main_wallet: MainWallet, sweep: Sweep) -> dict[str, Any]:
    client = _get_bep20_client()
    if client is None:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "BEP20 RPC is unavailable. Configure BEP20_RPC_URL in environment."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}
    if Account is None:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "eth-account is unavailable."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    wallet_key = _normalize_hex_key(wallet.private_key)
    try:
        wallet_account = Account.from_key(wallet_key)
    except Exception:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "Wallet private key is invalid."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    from_address = _to_checksum_address(client, wallet_account.address)
    to_address = _to_checksum_address(client, main_wallet.address)
    token_address = _to_checksum_address(client, BEP20_USDT_CONTRACT)
    if not from_address or not to_address or not token_address:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "BEP20 wallet/token address is invalid."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    contract = client.eth.contract(address=token_address, abi=ERC20_ABI)
    try:
        raw_balance = int(contract.functions.balanceOf(from_address).call())
    except Exception as exc:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = f"Failed to read BEP20 token balance: {exc}"
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    if raw_balance <= 0:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "No on-chain USDT balance to transfer."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    try:
        nonce = client.eth.get_transaction_count(from_address)
        gas_price = client.eth.gas_price
        transfer_fn = contract.functions.transfer(to_address, raw_balance)
        gas_limit = int(transfer_fn.estimate_gas({"from": from_address}))
        tx = transfer_fn.build_transaction(
            {
                "chainId": client.eth.chain_id,
                "from": from_address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
            }
        )
        signed = client.eth.account.sign_transaction(tx, private_key=wallet_key)
        raw_tx = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        tx_hash = client.eth.send_raw_transaction(raw_tx)
        receipt = client.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    except Exception as exc:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = f"Sweep transaction failed: {exc}"
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    if int(receipt.status) != 1:
        sweep.status = Sweep.Status.FAILED
        sweep.error_message = "BEP20 sweep failed on-chain."
        sweep.completed_at = timezone.now()
        sweep.save(update_fields=["status", "error_message", "completed_at"])
        return {"ok": False, "message": sweep.error_message, "sweep": sweep}

    decimals_factor = Decimal(10) ** Decimal(max(BEP20_USDT_DECIMALS, 0))
    transferred_amount = _safe_decimal(raw_balance) / decimals_factor
    wallet.balance = Decimal("0")
    wallet.save(update_fields=["balance", "updated_at"])

    sweep.status = Sweep.Status.SUCCESS
    sweep.txid = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    sweep.amount = transferred_amount
    sweep.completed_at = timezone.now()
    sweep.save(update_fields=["status", "txid", "amount", "completed_at"])
    return {
        "ok": True,
        "message": f"Swept {transferred_amount} USDT to main wallet: {main_wallet.address}.",
        "sweep": sweep,
    }


def get_public_usdt_balance(network: str, address: str) -> Decimal:
    selected_network = normalize_network(network)
    if selected_network == Wallet.Network.TRON:
        try:
            contract = _get_tron_usdt_contract()
        except Exception:
            return Decimal("0")
        if contract is None:
            return Decimal("0")
        try:
            raw = contract.functions.balanceOf(address)
        except Exception:
            return Decimal("0")
        return _safe_decimal(raw) / Decimal("1000000")

    if selected_network == Wallet.Network.BEP20:
        client = _get_bep20_client()
        if client is None:
            return Decimal("0")
        owner = _to_checksum_address(client, address)
        token = _to_checksum_address(client, BEP20_USDT_CONTRACT)
        if not owner or not token:
            return Decimal("0")
        try:
            contract = client.eth.contract(address=token, abi=ERC20_ABI)
            raw = contract.functions.balanceOf(owner).call()
        except Exception:
            return Decimal("0")
        decimals_factor = Decimal(10) ** Decimal(max(BEP20_USDT_DECIMALS, 0))
        return _safe_decimal(raw) / decimals_factor

    return Decimal("0")


def get_public_native_balance(network: str, address: str) -> Decimal:
    selected_network = normalize_network(network)
    if selected_network == Wallet.Network.TRON:
        balance = _get_trx_balance(address)
        return balance if balance is not None else Decimal("0")

    if selected_network == Wallet.Network.BEP20:
        balance = _get_bep20_native_balance(address)
        return balance if balance is not None else Decimal("0")

    return Decimal("0")


def get_relayer_balance_snapshot(network: str) -> dict[str, Any]:
    selected_network = normalize_network(network)
    relayer = get_or_create_relayer(selected_network)
    native_symbol = "TRX" if selected_network == Wallet.Network.TRON else "BNB"

    snapshot: dict[str, Any] = {
        "network": selected_network,
        "address": relayer.address,
        "is_enabled": relayer.is_enabled,
        "is_configured": relayer.is_configured,
        "native_symbol": native_symbol,
        "token_symbol": "USDT",
        "native_balance": "0",
        "token_balance": "0",
        "ok": False,
        "message": "",
    }

    if not relayer.address:
        snapshot["message"] = "Relayer address is not set."
        return snapshot

    if selected_network == Wallet.Network.BEP20 and _get_bep20_client() is None:
        snapshot["message"] = "BEP20 RPC is unavailable. Configure BEP20_RPC_URL in environment."
        return snapshot

    try:
        native_balance = get_public_native_balance(selected_network, relayer.address)
        token_balance = get_public_usdt_balance(selected_network, relayer.address)
    except Exception as exc:
        snapshot["message"] = str(exc)
        return snapshot

    snapshot["native_balance"] = str(native_balance)
    snapshot["token_balance"] = str(token_balance)
    snapshot["ok"] = True
    return snapshot
