"""
Broker Abstraction Layer for Indian Stock Brokers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ProductType(str, Enum):
    MIS = "MIS"      # Margin Intraday Square-off
    CNC = "CNC"      # Cash and Carry (Delivery)
    NRML = "NRML"    # Normal (F&O)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    TRIGGER_PENDING = "TRIGGER_PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    symbol: str
    transaction_type: TransactionType
    quantity: int
    exchange: str = "NSE"
    order_type: OrderType = OrderType.MARKET
    product: ProductType = ProductType.MIS
    price: float = 0.0
    trigger_price: float = 0.0
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "transaction_type": str(self.transaction_type),
            "order_type": str(self.order_type),
            "product": str(self.product),
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "status": str(self.status),
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "rejection_reason": self.rejection_reason
        }


class BaseBroker:
    """
    Abstract interface for broker API connections.
    """

    def authenticate(self) -> bool:
        raise NotImplementedError

    def place_order(self, order: Order) -> Order:
        raise NotImplementedError

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Order:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    def get_order_status(self, order_id: str) -> Order:
        raise NotImplementedError

    def get_positions(self) -> List[dict]:
        raise NotImplementedError

    def get_margins(self) -> dict:
        raise NotImplementedError
