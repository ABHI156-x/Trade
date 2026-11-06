# Indian Broker API Integration & Live Execution Guide

This guide details how to integrate the platform with official Indian discount brokers (Zerodha Kite Connect and Angel One SmartAPI), automate authentication with TOTP, and transition safely from paper trading to live order execution.

---

## 1. Supported Broker APIs

| Broker | API Product | Authentication | Intraday Product | WebSocket Feed |
| :--- | :--- | :--- | :--- | :--- |
| **Zerodha** | Kite Connect API 3 | API Key + Request Token / TOTP | `MIS` | Binary KiteTicker |
| **Angel One** | SmartAPI | API Key + Client Code + TOTP -> JWT | `INTRADAY` | SmartStream (Protobuf/JSON) |

---

## 2. Zerodha Kite Connect Integration

### Setup & Credentials
1. Register a developer account at [kite.trade](https://kite.trade).
2. Create an App to receive your **API Key** and **API Secret**.
3. Add credentials to your `.env` file:
   ```ini
   BROKER_NAME=zerodha
   BROKER_API_KEY=your_kite_api_key
   BROKER_API_SECRET=your_kite_api_secret
   ```

### Daily Access Token Generation
Zerodha requires generating a new access token every morning before market hours (09:15 IST).

Automated login flow with TOTP:
```python
import pyotp
import requests
from src.broker.zerodha_broker import ZerodhaBroker

# 1. Generate current TOTP code from secret
totp = pyotp.TOTP("YOUR_TOTP_SECRET")
current_totp = totp.now()

# 2. Complete daily login flow to obtain access_token
# (Store access token in .env or session cache)
access_token = "GENERATED_DAILY_ACCESS_TOKEN"

# 3. Instantiate broker
broker = ZerodhaBroker(
    api_key="your_kite_api_key",
    access_token=access_token,
    is_mock=False
)
broker.authenticate()
```

---

## 3. Angel One SmartAPI Integration

### Setup & Credentials
1. Register at [smartapi.angelone.in](https://smartapi.angelone.in).
2. Create an API App to receive your **API Key**.
3. Add credentials to your `.env` file:
   ```ini
   BROKER_NAME=angelone
   ANGEL_API_KEY=your_angel_api_key
   ANGEL_CLIENT_CODE=your_client_code
   ANGEL_PASSWORD=your_trading_pin
   ANGEL_TOTP_SECRET=your_totp_secret
   ```

### Daily JWT Generation
```python
import pyotp
import requests
from src.broker.angel_one_broker import AngelOneBroker

totp = pyotp.TOTP("YOUR_TOTP_SECRET")

# Login endpoint gives JWT Auth Token and Refresh Token
login_payload = {
    "clientcode": "YOUR_CLIENT_CODE",
    "password": "YOUR_TRADING_PIN",
    "totp": totp.now()
}
# Send to SmartAPI login endpoint...
jwt_token = "GENERATED_JWT_TOKEN"

broker = AngelOneBroker(
    api_key="your_angel_api_key",
    client_code="YOUR_CLIENT_CODE",
    jwt_token=jwt_token,
    is_mock=False
)
broker.authenticate()
```

---

## 4. Live Order Execution Safety Rules

> [!CAUTION]
> Algorithmic trading with real capital carries significant financial risk. Live execution must never be activated without completing rigorous paper trading validation and stress testing.

The platform provides an `OrderExecutionEngine` with five mandatory safety layers:

```
[ Incoming Signal ]
         │
         ▼
[ 1. Kill-Switch Gate ] ──── If Engaged ───► REJECT ORDER
         │
         ▼
[ 2. Market Hours Gate ] ─── If Outside 09:15-15:15 ───► REJECT ORDER
         │
         ▼
[ 3. Fat-Finger Check ] ──── If Value > ₹50,000 ───► REJECT ORDER
         │
         ▼
[ 4. Daily Turnover ] ────── If Total > ₹200,000 ───► REJECT ORDER
         │
         ▼
[ 5. Risk Guard Check ] ──── If Daily Loss Limit Hit ───► REJECT ORDER
         │
         ▼
[ Safe Order Dispatched to Broker ]
```

### Steps to Safely Enable Live Execution

1. **Step 1 – Dry Run Validation**:
   Always run in `dry_run=True` mode first:
   ```python
   engine = OrderExecutionEngine(broker=broker, dry_run=True)
   ```
   Orders will be logged and audited without sending real orders.

2. **Step 2 – Explicit Kill-Switch Disengagement**:
   To enable live orders, you must explicitly pass the confirmation passphrase:
   ```python
   engine = OrderExecutionEngine(broker=broker, dry_run=False)
   engine.disengage_kill_switch("I_CONFIRM_LIVE_TRADING")
   ```

3. **Step 3 – Immediate Kill-Switch Re-engagement**:
   At any time, you can trigger an emergency stop:
   ```python
   engine.engage_kill_switch(reason="Manual intervention")
   ```
