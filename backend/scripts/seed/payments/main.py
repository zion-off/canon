"""Payments service."""

import time
from dataclasses import dataclass
from typing import Protocol


class InventoryService(Protocol):
    def check_stock(self, product_id: str) -> int: ...


class PaymentGateway(Protocol):
    def process_payment(self, amount: float, customer_id: str) -> bool: ...


@dataclass
class PaymentRequest:
    order_id: str
    customer_id: str
    amount: float
    product_id: str


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str | None
    error: str | None


class PaymentsService:
    def __init__(self, inventory: InventoryService, gateway: PaymentGateway):
        self.inventory = inventory
        self.gateway = gateway
        self.max_retries = 3
        self.retry_delay_ms = 500

    def process_payment(self, request: PaymentRequest) -> PaymentResult:
        stock = self._check_inventory_with_retries(request.product_id)

        if stock <= 0:
            return PaymentResult(
                success=False,
                transaction_id=None,
                error="Insufficient inventory",
            )

        try:
            success = self.gateway.process_payment(
                request.amount,
                request.customer_id,
            )
            if success:
                return PaymentResult(
                    success=True,
                    transaction_id=f"txn_{request.order_id}",
                    error=None,
                )
            return PaymentResult(
                success=False,
                transaction_id=None,
                error="Payment gateway declined",
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                transaction_id=None,
                error=f"Payment failed: {e}",
            )

    def _check_inventory_with_retries(self, product_id: str) -> int:
        last_exception: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return self.inventory.check_stock(product_id)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_ms / 1000.0)

        raise last_exception or RuntimeError("Inventory check failed")

    def process_batch(self, requests: list[PaymentRequest]) -> list[PaymentResult]:
        results = []
        for request in requests:
            result = self.process_payment(request)
            results.append(result)
        return results
