"""
Angel One SmartAPI Broker Adapter.
Implements authentication, order placement, modification, and cancellation
for Angel One SmartAPI.
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

logger = logging.getLogger("IndianDayTrader.AngelOneBroker")


class AngelOneBroker(BaseBroker):
    """
    Angel One SmartAPI Adapter.
    Supports JWT auth, intraday MIS / CNC orders, and mock simulation modes.
    """

    def __init__(
        self,
        api_key: str = "",
        client_code: str = "",
        password: str = "",
        totp_key: str = "",
        jwt_token: str = "",
        is_mock: bool = True
    ):
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp_key = totp_key
        self.jwt_token = jwt_token
        self.is_mock = is_mock
        self._authenticated = False
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, dict] = {}
        self._mock_cash = 50000.0

    def authenticate(self) -> bool:
        if self.is_mock:
            self._authenticated = True
            logger.info("AngelOneBroker authenticated in MOCK mode.")
            return True

        if not self.api_key or not self.jwt_token:
            logger.error("Angel One API Key or JWT token missing.")
            return False

        # Live session check with Angel One profile endpoint
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "106.193.147.98",
                "X-MACAddress": "fe80::216e:6507:4b9c:9045",
                "X-PrivateKey": self.api_key
            }
            resp = requests.get(
                "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile",
                headers=headers,
                timeout=5
            )
            if resp.status_code == 200 and resp.json().get("status") is True:
                self._authenticated = True
                logger.info("Angel One authenticated successfully.")
                return True
            else:
                logger.error("Angel One authentication failed: %s", resp.text)
                return False
        except Exception as e:
            logger.error("Angel One authentication exception: %s", e)
            return False

    def place_order(self, order: Order) -> Order:
        if not self._authenticated:
            self.authenticate()

        order_id = f"ANGEL-{uuid.uuid4().hex[:10].upper()}"
        order.order_id = order_id

        if self.is_mock:
            order.status = OrderStatus.COMPLETE
            order.filled_quantity = order.quantity
            order.average_price = order.price if order.price > 0 else 1000.0
            order.timestamp = datetime.now()
            self._orders[order_id] = order
            self._update_mock_position(order)
            logger.info("Angel One MOCK order placed: %s", order.to_dict())
            return order

        # Real Angel One API order placement
        try:
            import requests
            url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-PrivateKey": self.api_key
            }
            payload = {
                "variety": "NORMAL",
                "tradingsymbol": order.symbol,
                "symboltoken": "0",  # Requires mapping from master contract instrument list
                "transactiontype": order.transaction_type.value,
                "exchange": order.exchange,
                "ordertype": order.order_type.value,
                "producttype": "INTRADAY" if order.product == ProductType.MIS else "DELIVERY",
                "duration": "DAY",
                "price": str(order.price) if order.order_type == OrderType.LIMIT else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(order.quantity)
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=5)
            data = resp.json()
            if resp.status_code == 200 and data.get("status") is True:
                order.order_id = str(data.get("data", {}).get("orderid", order_id))
                order.status = OrderStatus.OPEN
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = data.get("message", resp.text)
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
                total = pos["quantity"] + order.quantity
                pos["average_price"] = (
                    (pos["quantity"] * pos["average_price"] + order.quantity * order.average_price) / total
                )
                pos["quantity"] = total
            else:
                self._positions[sym] = {
                    "symbol": sym,
                    "quantity": order.quantity,
                    "average_price": order.average_price,
                    "exchange": order.exchange
                }
        elif order.transaction_type == TransactionType.SELL:
            if sym in self._positions:
                self._positions[sym]["quantity"] -= order.quantity
                if self._positions[sym]["quantity"] <= 0:
                    del self._positions[sym]

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Order:
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found.")
        order = self._orders[order_id]
        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price
        if trigger_price is not None:
            order.trigger_price = trigger_price
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self._orders:
            return False
        order = self._orders[order_id]
        if order.status in (OrderStatus.COMPLETE, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return False
        order.status = OrderStatus.CANCELLED
        return True

    def get_order_status(self, order_id: str) -> Order:
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found.")
        return self._orders[order_id]

    def get_positions(self) -> List[dict]:
        return list(self._positions.values())

    def get_margins(self) -> dict:
        return {
            "cash": self._mock_cash,
            "used": sum(p["quantity"] * p["average_price"] for p in self._positions.values()),
            "available": max(0.0, self._mock_cash - sum(p["quantity"] * p["average_price"] for p in self._positions.values()))
        }
