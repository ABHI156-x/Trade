"""
Safe Live Order Execution Engine.

Implements multi-tiered safety gates before any order reaches a live broker API:
  - Hardware / Software Kill-Switch
  - Fat-Finger / Max Value & Quantity Bounds
  - Pre-Trade Risk Checks (Daily loss limit, max trades, circuit breaker)
  - Intraday Market Session & Auto-Square-Off Timing
  - Dry-Run / Paper Simulation Safety Mode
  - Full Execution Audit Trail
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from src.broker.base_broker import BaseBroker, Order, OrderStatus, OrderType, TransactionType
from src.risk.advanced_risk_guard import AdvancedRiskGuard
from src.utils.market_session import is_market_session, is_entry_allowed, is_square_off_time

logger = logging.getLogger("IndianDayTrader.OrderExecutionEngine")


class OrderExecutionEngine:
    """
    Guards and manages execution of live orders with strict safety checks.
    """

    def __init__(
        self,
        broker: BaseBroker,
        risk_guard: Optional[AdvancedRiskGuard] = None,
        max_order_value: float = 50000.0,
        max_order_quantity: int = 500,
        max_daily_turnover: float = 200000.0,
        dry_run: bool = True,
        enforce_market_hours: bool = True
    ):
        self.broker = broker
        self.risk_guard = risk_guard
        self.max_order_value = max_order_value
        self.max_order_quantity = max_order_quantity
        self.max_daily_turnover = max_daily_turnover
        self.dry_run = dry_run
        self.enforce_market_hours = enforce_market_hours

        # Kill Switch is ENGAGED by default for safety
        self._kill_switch_engaged = True
        if os.getenv("LIVE_ORDER_EXECUTION_ENABLED", "false").lower() == "true":
            self._kill_switch_engaged = False

        self.daily_turnover = 0.0
        self.audit_log: List[dict] = []

    @property
    def is_kill_switch_engaged(self) -> bool:
        return self._kill_switch_engaged

    def disengage_kill_switch(self, confirmation: str) -> bool:
        """
        Requires explicit confirmation keyword 'I_CONFIRM_LIVE_TRADING'.
        """
        if confirmation == "I_CONFIRM_LIVE_TRADING":
            self._kill_switch_engaged = False
            logger.warning("SAFETY ALERT: Kill switch disengaged. Live trading order execution is ENABLED.")
            return True
        logger.error("Failed to disengage kill switch: Invalid confirmation code.")
        return False

    def engage_kill_switch(self, reason: str = "User manual trigger"):
        self._kill_switch_engaged = True
        logger.warning("SAFETY ALERT: Kill switch ENGAGED (%s). All future orders blocked.", reason)

    def validate_pre_trade_safety(self, order: Order, current_price: float) -> Tuple[bool, str]:
        """
        Runs comprehensive pre-trade validation checks.
        """
        # 1. Kill Switch Check
        if self._kill_switch_engaged and not self.dry_run:
            return False, "SAFETY BLOCK: Kill switch is ENGAGED. Live order routing disabled."

        # 2. Market Hours Check
        now = order.timestamp if isinstance(order.timestamp, datetime) else datetime.now()
        if self.enforce_market_hours:
            if not is_market_session(now):
                return False, f"SAFETY BLOCK: Outside market hours ({now.strftime('%H:%M')})."
            if order.transaction_type == TransactionType.BUY and not is_entry_allowed(now):
                return False, f"SAFETY BLOCK: Past entry cutoff (15:15 IST)."

        # 3. Quantity check
        if order.quantity <= 0:
            return False, f"SAFETY BLOCK: Invalid order quantity ({order.quantity})."
        if order.quantity > self.max_order_quantity:
            return False, f"SAFETY BLOCK: Quantity ({order.quantity}) exceeds max limit ({self.max_order_quantity})."

        # 4. Fat-finger single order value check
        order_price = order.price if order.price > 0 else current_price
        order_val = order_price * order.quantity
        if order_val > self.max_order_value:
            return False, f"FAT-FINGER BLOCK: Order value ₹{order_val:.2f} exceeds limit ₹{self.max_order_value:.2f}."

        # 5. Daily Turnover Check
        if self.daily_turnover + order_val > self.max_daily_turnover:
            return False, f"SAFETY BLOCK: Daily turnover ₹{self.daily_turnover + order_val:.2f} exceeds limit ₹{self.max_daily_turnover:.2f}."

        # 6. Advanced Risk Guard Check
        if self.risk_guard is not None:
            allowed, risk_reason = self.risk_guard.can_take_trade()
            if not allowed:
                return False, f"RISK GUARD BLOCK: {risk_reason}"

        return True, "Pre-trade safety checks passed"

    def execute_order(self, order: Order, current_price: float) -> Order:
        """
        Executes order through safety checks and submits to broker or dry-run simulator.
        """
        passed, reason = self.validate_pre_trade_safety(order, current_price)
        order_price = order.price if order.price > 0 else current_price
        order_val = order_price * order.quantity

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": order.symbol,
            "transaction_type": str(order.transaction_type),
            "quantity": order.quantity,
            "price": order_price,
            "order_value": order_val,
            "passed_safety": passed,
            "reason": reason,
            "dry_run": self.dry_run
        }

        if not passed:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            audit_entry["order_status"] = str(OrderStatus.REJECTED)
            self.audit_log.append(audit_entry)
            logger.warning("Order execution REJECTED: %s", reason)
            return order

        # If Dry Run mode, simulate successful routing without sending to broker
        if self.dry_run:
            order.status = OrderStatus.COMPLETE
            order.filled_quantity = order.quantity
            order.average_price = order_price
            order.order_id = f"DRYRUN-{len(self.audit_log) + 1}"
            audit_entry["order_status"] = "DRY_RUN_COMPLETE"
            self.daily_turnover += order_val
            self.audit_log.append(audit_entry)
            logger.info("Order executed in DRY-RUN mode: %s", order.to_dict())
            return order

        # Live execution through broker
        placed_order = self.broker.place_order(order)
        self.daily_turnover += order_val
        audit_entry["order_status"] = str(placed_order.status)
        audit_entry["broker_order_id"] = placed_order.order_id
        self.audit_log.append(audit_entry)
        return placed_order
