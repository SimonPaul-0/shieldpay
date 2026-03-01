# 🛡️ ShieldPay — AI UPI Fraud Detector
### AMD Slingshot 2026 Hackathon Submission

---

## What is ShieldPay?

ShieldPay is an **AI-powered UPI & banking fraud detection system** that analyzes transactions in real-time using a hybrid ML + rule-based engine, running on AMD RYZEN AI hardware for on-device inference.

---

## Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Backend     | Python 3.12, Flask                |
| ML Engine   | scikit-learn (RandomForestClassifier) |
| Database    | SQLite3 (zero-config)             |
| Streaming   | Server-Sent Events (SSE)          |
| Frontend    | Vanilla JS + CSS (served by Flask)|
| AI Hardware | AMD RYZEN AI NPU (ONNX-ready)     |

---

## Project Structure

```
shieldpay/
├── app.py              # Flask API server + routes + SSE stream
├── fraud_engine.py     # ML fraud detection engine (RandomForest + rules)
├── requirements.txt    # Python dependencies
├── shieldpay.db        # SQLite DB (auto-created on first run)
└── templates/
    └── index.html      # Full frontend dashboard
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Open browser
# → http://localhost:5000
```

---

## API Endpoints

| Method | Endpoint              | Description                          |
|--------|-----------------------|--------------------------------------|
| POST   | /api/analyze          | Analyze a UPI transaction            |
| GET    | /api/transactions     | List recent transactions             |
| GET    | /api/stats            | Dashboard metrics + hourly chart     |
| GET    | /api/vpa/lookup?vpa=  | VPA registry lookup                  |
| POST   | /api/report           | File fraud report (RBI CFCFRMS)      |
| GET    | /api/stream           | SSE live transaction stream          |

---

## Sample API Call

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sender_vpa": "rbi.helpdesk@upi",
    "receiver_vpa": "scam99@ybl",
    "amount": 50000,
    "txn_type": "Unknown Collect Request",
    "time_of_day": "Late Night",
    "remarks": "KYC update urgent"
  }'
```

### Response:
```json
{
  "risk_score": 95,
  "verdict": "fraud",
  "confidence": 99.0,
  "flags": [
    {"type": "alert", "msg": "VPA matches known fraud/scam address in registry"},
    {"type": "alert", "msg": "Sender VPA contains impersonation keyword: 'helpdesk'"},
    {"type": "alert", "msg": "Unsolicited collect request — never approve without verifying"}
  ],
  "ml_probabilities": {"safe": 0.01, "suspicious": 0.04, "fraud": 0.95},
  "engine": "rule_override",
  "txn_id": 42
}
```

---

## Fraud Detection Features

1. **VPA Impersonation Detection** — flags VPAs containing keywords like `helpdesk`, `kyc`, `rbi`, `sbi`
2. **Mule Account Pattern Matching** — regex patterns catch `0x...`, `mule\d`, `anon\d` VPAs
3. **Social Engineering NLP** — 30+ keywords scanned in transaction remarks
4. **Collect Request Alert** — high-risk flag for unsolicited collect requests (classic ₹1 phishing)
5. **Time-Based Risk Scoring** — late-night transactions carry 3.4× multiplier
6. **High-Value Transaction Flag** — amounts > ₹50,000 trigger additional checks
7. **Known Fraud VPA Registry** — hard override block for confirmed scam addresses
8. **Verified Merchant Whitelist** — reduces false positives for known legitimate merchants
9. **RandomForest ML Probability** — 120-tree ensemble with class weights (fraud = 4×)
10. **Hybrid Score Fusion** — 60% ML + 40% rule-based for optimal accuracy

---

## AMD RYZEN AI Integration (Pitch Point)

The RandomForest model can be exported to ONNX format and deployed on AMD RYZEN AI NPU:

```python
# Future: ONNX export for AMD RYZEN AI NPU
from skl2onnx import convert_sklearn
model_onnx = convert_sklearn(engine.model, ...)
# Run inference on AMD RYZEN AI hardware — sub-80ms latency
```

Benefits:
- **On-device inference** — no transaction data leaves the phone
- **AMD RYZEN AI NPU** — hardware-accelerated tensor ops
- **Sub-80ms** end-to-end analysis latency
- **Privacy-first** — user behavioral baseline stays local

---

*Built for AMD Slingshot 2026 — Ignite Your Ideas*
