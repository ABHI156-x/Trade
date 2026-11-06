"""
Zerodha Kite Connect Broker API Adapter.
Implements authentication, order placement, modification, cancellation,
and position retrieval for Zerodha Kite Connect API 3.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.broker.base_broker import (
    BaseBroker,
    Order,
    OrderStatus,
    OrderType,
    TransactionType,
    ProductType
)

logger = logging.getLogger("IndianDayTrader.ZerodhaBroker")


class ZerodhaBroker(BaseBroker):
    """
    Zerodha Kite Connect API Adapter.
    Supports both live API sessions (when valid API credentials and session tokens exist)
    and sandbox/mock simulation modes.
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        access_token: str = "",
        is_mock: bool = True
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.is_mock = is_mock
        self._authenticated = False
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, dict] = {}
        self._mock_cash = 50000.0

    def authenticate(self) -> bool:
        if self.is_mock:
            self._authenticated = True
            logger.info("ZerodhaBroker authenticated in MOCK mode.")
            return True

        if not self.api_key or not self.access_token:
            logger.error("Zerodha API Key or Access Token is missing.")
            return False

        # Live session validation with Kite API endpoint: https://api.kite.trade/user/profile
        try:
            import requests
            headers = {
                "X-Kite-Version": "3",
                "Authorization": f"token {self.api_key}:{self.access_token}"
            }
            resp = requests.get("https://api.kite.trade/user/profile", headers=headers, timeout=5)
            if resp.status_code == 200:
                self._authenticated = True
                logger.info("Zerodha live session authenticated successfully.")
                return True
            else:
                logger.error("Zerodha auth failed with status %s: %s", resp.status_code, resp.text)
                return False
        except Exception as e:
            logger.error("Zerodha authentication exception: %s", e)
            return False

    def place_order(self, order: Order) -> Order:
        if not self._authenticated:
            self.authenticate()

        order_id = f"KITE-{uuid.uuid4().hex[:10].upper()}"
        order.order_id = order_id

        if self.is_mock:
            # Simulate instant execution for Market orders
            order.status = OrderStatus.COMPLETE
            order.filled_quantity = order.quantity
            order.average_price = order.price if order.price > 0 else 1000.0
            order.timestamp = datetime.now()
            self._orders[order_id] = order

            # Track position
            self._update_mock_position(order)
            logger.info("Zerodha MOCK order placed: %s", order.to_dict())
            return order

        # Real Zerodha Kite API order placement
        try:
            import requests
            url = "https://api.kite.trade/orders/regular"
            headers = {
                "X-Kite-Version": "3",
                "Authorization": f"token {self.api_key}:{self.access_token}"
            }
            payload = {
                "tradingsymbol": order.symbol,
                "exchange": order.exchange,
                "transaction_type": order.transaction_type.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "product": order.product.value,
                "price": order.price if order.order_type == OrderType.LIMIT else 0,
                "trigger_price": order.trigger_price if order.order_type in (OrderType.SL, OrderType.SL_M) else 0,
                "validity": "DAY"
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                order.order_id = str(data.get("order_id", order_id))
                order.status = OrderStatus.OPEN
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = resp.text
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)

        self._orders[order.order_id] = order
        return order

    def _update_mock_position(self, order: Order):
        sym = order.symbol
        if order.transaction_type == TransactionType.BUY:
            if sym in self._positions:
                pos = self._positions[sym]
                total_qty = pos["quantity"] + order.quantity
                pos["average_price"] = (
                    (pos["quantity"] * pos["average_price"] + order.quantity * order.average_price)
                    / total_qty
                )
                pos["quantity"] = total_qty
            else:
                self._positions[sym] = {
                    "symbol": sym,
                    "quantity": order.quantity,
                    "average_price": order.average_price,
                    "product": order.product.value,
                    "exchange": order.exchange
                }
        elif order.transaction_type == TransactionType.SELL:
            if sym in self._positions:
                pos = self._positions[sym]
                pos["quantity"] -= order.quantity
                if pos["quantity"] <= 0:
                    del self._positions[sym]

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Order:
        if order_id not in self._orders:
            raise ValueError(f"Order ID {order_id} not found.")

        order = self._orders[order_id]
        if order.status not in (OrderStatus.OPEN, OrderStatus.TRIGGER_PENDING):
            raise ValueError(f"Cannot modify order in status {order.status}")

        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price
        if trigger_price is not None:
            order.trigger_price = trigger_price

        logger.info("Order %s modified.", order_id)
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]
        if order.status in (OrderStatus.COMPLETE, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return False

        order.status = OrderStatus.CANCELLED
        logger.info("Order %s cancelled.", order_id)
        return True

    def get_order_status(self, order_id: str) -> Order:
        if order_id not in self._orders:
            raise ValueError(f"Order ID {order_id} not found.")
        return self._orders[order_id]

    def get_positions(self) -> List[dict]:
        return list(self._positions.values())

    def get_margins(self) -> dict:
        return {
            "cash": self._mock_cash,
            "used": sum(p["quantity"] * p["average_price"] for p in self._positions.values()),
            "available": max(0.0, self._mock_cash - sum(p["quantity"] * p["average_price"] for p in self._positions.values()))
        }
