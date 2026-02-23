from django.test import SimpleTestCase

from wallet.services import (
    BEP20_AUTOCHECK_LOOKBACK_BLOCKS,
    BEP20_INITIAL_LOOKBACK_BLOCKS,
    _calculate_affordable_native_transfer_wei,
    _decode_hex_message,
    _decode_log_uint256,
    _resolve_bep20_scan_start_block,
    _set_deposit_result_message,
    _tron_tx_error_message,
    build_qr_payload,
)


class BuildQrPayloadTests(SimpleTestCase):
    def test_returns_raw_trimmed_address_for_tron(self):
        address = "  TQj...abc123  "
        self.assertEqual(build_qr_payload("tron", address), "TQj...abc123")

    def test_returns_raw_trimmed_address_for_bep20(self):
        address = "  0x1234567890abcdef  "
        self.assertEqual(build_qr_payload("bep20", address), "0x1234567890abcdef")

    def test_returns_empty_for_blank_address(self):
        self.assertEqual(build_qr_payload("tron", "   "), "")


class DecodeLogUint256Tests(SimpleTestCase):
    def test_decodes_from_bytes(self):
        self.assertEqual(_decode_log_uint256(bytes.fromhex("000000000000000000000000000000000000000000000000000000000000000a")), 10)

    def test_decodes_from_hex_string(self):
        self.assertEqual(_decode_log_uint256("0x0f"), 15)

    def test_returns_zero_for_invalid_value(self):
        self.assertEqual(_decode_log_uint256("not-hex"), 0)


class AffordableTransferWeiTests(SimpleTestCase):
    def test_caps_by_requested_value(self):
        # balance 1.0 BNB, fee 0.000021 BNB, request 0.1 BNB -> send 0.1
        result = _calculate_affordable_native_transfer_wei(
            sender_balance_wei=10**18,
            gas_price_wei=10**9,
            gas_limit=21000,
            requested_value_wei=10**17,
        )
        self.assertEqual(result, 10**17)

    def test_caps_by_available_balance_after_fee(self):
        # balance 0.015484 BNB, fee 0.000021 BNB, request 3 BNB -> send max affordable
        result = _calculate_affordable_native_transfer_wei(
            sender_balance_wei=15484000000000000,
            gas_price_wei=10**9,
            gas_limit=21000,
            requested_value_wei=3000000000000000000,
        )
        self.assertEqual(result, 15463000000000000)

    def test_returns_zero_when_fee_exceeds_balance(self):
        result = _calculate_affordable_native_transfer_wei(
            sender_balance_wei=10000,
            gas_price_wei=10**9,
            gas_limit=21000,
            requested_value_wei=1000000,
        )
        self.assertEqual(result, 0)

    def test_keeps_configured_reserve(self):
        # balance 0.02 BNB, fee 0.000021 BNB, reserve 0.01 BNB -> max send 0.009979 BNB
        result = _calculate_affordable_native_transfer_wei(
            sender_balance_wei=20000000000000000,
            gas_price_wei=10**9,
            gas_limit=21000,
            requested_value_wei=3000000000000000000,
            reserve_wei=10000000000000000,
        )
        self.assertEqual(result, 9979000000000000)


class ResolveBep20ScanStartBlockTests(SimpleTestCase):
    def test_prefers_last_scanned_cursor(self):
        result = _resolve_bep20_scan_start_block(
            latest_block=1000,
            last_confirmed_block=400,
            last_scanned_block=900,
        )
        self.assertEqual(result, 901)

    def test_uses_last_confirmed_when_scanned_is_zero(self):
        result = _resolve_bep20_scan_start_block(
            latest_block=1000,
            last_confirmed_block=555,
            last_scanned_block=0,
        )
        self.assertEqual(result, 556)

    def test_falls_back_to_initial_lookback_for_first_scan(self):
        result = _resolve_bep20_scan_start_block(
            latest_block=5000,
            last_confirmed_block=0,
            last_scanned_block=0,
        )
        expected = max(0, 5000 - max(BEP20_INITIAL_LOOKBACK_BLOCKS, BEP20_AUTOCHECK_LOOKBACK_BLOCKS, 1) + 1)
        self.assertEqual(result, expected)


class DepositResultMessageTests(SimpleTestCase):
    def test_single_deposit_message_contains_amount(self):
        result = {"created": 1, "created_amount": "8.85000000", "message": ""}
        _set_deposit_result_message(result)
        self.assertEqual(result["message"], "Deposit received: 8.85 USDT credited to your balance.")

    def test_multiple_deposits_message_contains_count_and_total(self):
        result = {"created": 3, "created_amount": "12.50000000", "message": ""}
        _set_deposit_result_message(result)
        self.assertEqual(
            result["message"],
            "Deposits received: 3 transactions, total 12.5 USDT credited to your balance.",
        )


class TronTxErrorMessageTests(SimpleTestCase):
    def test_decodes_hex_res_message(self):
        decoded = _decode_hex_message("4f55545f4f465f454e45524759")
        self.assertEqual(decoded, "OUT_OF_ENERGY")

    def test_returns_empty_for_successful_tx(self):
        tx_result = {"receipt": {"result": "SUCCESS"}, "result": "SUCCESS"}
        self.assertEqual(_tron_tx_error_message(tx_result), "")

    def test_returns_out_of_energy_error_with_details(self):
        tx_result = {
            "receipt": {"result": "OUT_OF_ENERGY"},
            "result": "FAILED",
            "resMessage": "4e6f7420656e6f75676820656e65726779",
        }
        message = _tron_tx_error_message(tx_result)
        self.assertIn("OUT_OF_ENERGY", message)
        self.assertIn("Not enough energy", message)
