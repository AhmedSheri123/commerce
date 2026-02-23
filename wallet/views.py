import base64
import json
from decimal import Decimal
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from wallet.models import Deposit, Wallet
from wallet.services import (
    DEFAULT_DEPOSIT_NETWORK,
    build_qr_payload,
    check_wallet_deposits,
    ensure_user_network_wallet,
    ensure_user_wallets,
    get_network_meta,
    get_supported_networks,
    get_user_wallet,
    main_wallet_is_configured,
    normalize_network,
    relayer_is_configured,
    sweep_wallet_to_main,
    topup_wallet_gas,
    webhook_deposit,
)


def _build_qr_base64(network: str, address: str) -> str:
    if not address:
        return ""
    payload = build_qr_payload(network, address) or address
    qr = qrcode.make(payload)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _serialize_deposits(wallet: Wallet) -> list[dict]:
    deposits = wallet.deposits.all().order_by("-created_at")[:50]
    rows = []
    for dep in deposits:
        rows.append(
            {
                "network": dep.get_network_display(),
                "amount": str(dep.amount),
                "status": dep.status,
                "created_at": timezone.localtime(dep.created_at).strftime("%Y-%m-%d %H:%M"),
                "confirmed_at": timezone.localtime(dep.confirmed_at).strftime("%Y-%m-%d %H:%M")
                if dep.confirmed_at
                else "-",
            }
        )
    return rows


@login_required
def deposit_view(request):
    ensure_user_wallets(request.user)

    network_meta = get_network_meta(request.GET.get("network", DEFAULT_DEPOSIT_NETWORK))
    selected_network = network_meta["key"]
    wallet, _ = ensure_user_network_wallet(request.user, selected_network)
    deposit_address = wallet.address

    qr_base64 = _build_qr_base64(selected_network, deposit_address)
    network_options = get_supported_networks(request.user)
    for option in network_options:
        option["is_selected"] = option["key"] == selected_network

    deposits = wallet.deposits.all().order_by("-created_at")

    return render(
        request,
        "dashboard/accounts/transactions/deposit.html",
        {
            "wallet": wallet,
            "wallet_balance": str(wallet.profile.balance),
            "deposits": deposits,
            "qr_code": qr_base64,
            "network_options": network_options,
            "selected_network": network_meta,
            "selected_network_key": selected_network,
            "deposit_address": deposit_address,
            "relayer_available": relayer_is_configured(selected_network),
            "main_wallet_available": main_wallet_is_configured(selected_network),
            "check_api_url": reverse("accounts:deposit_check_api"),
            "network_api_url": reverse("accounts:deposit_network_api"),
        },
    )


@login_required
@require_POST
def deposit_network_api(request):
    network_meta = get_network_meta(request.POST.get("network", DEFAULT_DEPOSIT_NETWORK))
    selected_network = network_meta["key"]
    wallet, _ = ensure_user_network_wallet(request.user, selected_network)
    deposit_address = wallet.address

    return JsonResponse(
        {
            "ok": True,
            "network": selected_network,
            "selected_network": network_meta,
            "deposit_address": deposit_address,
            "wallet_balance": str(wallet.profile.balance),
            "qr_code": _build_qr_base64(selected_network, deposit_address),
            "relayer_available": relayer_is_configured(selected_network),
            "main_wallet_available": main_wallet_is_configured(selected_network),
            "deposits": _serialize_deposits(wallet),
            "auto_check_supported": bool(network_meta.get("auto_check_supported")),
        }
    )


@login_required
@require_POST
def deposit_check_api(request):
    network = normalize_network(request.POST.get("network", DEFAULT_DEPOSIT_NETWORK))
    wallet = get_user_wallet(request.user, network)
    if wallet is None:
        wallet, _ = ensure_user_network_wallet(request.user, network)

    result = check_wallet_deposits(wallet)
    status_code = 200 if result.get("ok") else 500
    return JsonResponse(
        {
            "ok": result.get("ok", False),
            "network": network,
            "created": result.get("created", 0),
            "created_amount": str(result.get("created_amount", "0")),
            "processed": result.get("processed", 0),
            "message": result.get("message", ""),
        },
        status=status_code,
    )


@login_required
@require_POST
def relayer_topup_view(request):
    network = normalize_network(request.POST.get("network", DEFAULT_DEPOSIT_NETWORK))
    wallet = get_user_wallet(request.user, network)
    if wallet is None:
        wallet, _ = ensure_user_network_wallet(request.user, network)

    result = topup_wallet_gas(wallet)
    redirect_url = f"{reverse('accounts:deposit')}?network={network}"

    if result.get("ok"):
        if result.get("topped_up"):
            messages.success(request, result.get("message", "Relayer gas top-up completed."))
        else:
            messages.info(request, result.get("message", "Gas balance is already sufficient."))
    else:
        messages.error(request, result.get("message", "Relayer top-up failed."))
    return redirect(redirect_url)


@login_required
@require_POST
def sweep_to_main_view(request):
    network = normalize_network(request.POST.get("network", DEFAULT_DEPOSIT_NETWORK))
    wallet = get_user_wallet(request.user, network)
    if wallet is None:
        wallet, _ = ensure_user_network_wallet(request.user, network)

    result = sweep_wallet_to_main(wallet)
    redirect_url = f"{reverse('accounts:deposit')}?network={network}"
    if result.get("ok"):
        messages.success(request, result.get("message", "Sweep completed successfully."))
    else:
        messages.error(request, result.get("message", "Sweep failed."))
    return redirect(redirect_url)


@csrf_exempt
def deposit_webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "Invalid JSON."}, status=400)

    network = normalize_network(data.get("network", DEFAULT_DEPOSIT_NETWORK))
    to_address = data.get("to") or data.get("to_address") or ""
    txid = data.get("txid") or data.get("txID") or data.get("transaction_id") or ""
    token = str(data.get("token", "USDT")).upper()

    try:
        amount = Decimal(str(data.get("amount", "0")))
    except Exception:
        amount = Decimal("0")

    if token != "USDT" or not to_address or not txid or amount <= 0:
        return JsonResponse({"ok": False, "message": "Invalid payload."}, status=400)

    result = webhook_deposit(network=network, to_address=to_address, txid=txid, amount=amount, payload=data)
    if not result.get("ok"):
        return JsonResponse(result, status=404)
    return JsonResponse(result, status=200)


@login_required
def transfer_to_master_view(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id)
    if request.user.id != wallet.user_id and not request.user.is_superuser:
        messages.error(request, "You are not allowed to sweep this wallet.")
        return redirect("accounts:deposit")

    result = sweep_wallet_to_main(wallet)
    if result.get("ok"):
        messages.success(request, result.get("message", "Sweep completed successfully."))
    else:
        messages.error(request, result.get("message", "Sweep failed."))

    if request.user.is_superuser:
        return redirect("management:wallets")
    return redirect(f"{reverse('accounts:deposit')}?network={wallet.network}")
