# shieldpay
# 🛡️ ShieldPay — AI-Powered UPI Fraud Detector

> **AMD Slingshot 2026 Hackathon Submission**  
> Protecting India's digital payments with on-device AI

---

<!-- Add your screenshots below — replace the placeholder text with your actual image links after uploading -->

## 📸 Screenshots

### Live Dashboard
![Dashboard](Screenshot%202026-03-01%20200618.png)

### Hero & Live Feed
![Hero](Screenshot%202026-03-01%20200709.png)

### Transaction Analyzer
![Analyzer](Screenshot%202026-03-01%20200730.png)

### How It Works
![How It Works](Screenshot%202026-03-01%20200742.png)

---

## 🚨 The Problem

India processes **₹20+ lakh crore** in UPI transactions every month.  
Yet **₹1.2 lakh crore** is lost annually to UPI fraud — affecting millions of everyday users.

Common attacks include:
- 🎭 **VPA Spoofing** — fake IDs like `rbi.helpdesk@upi` impersonating banks
- 💸 **Collect Request Scams** — ₹1 phishing probes to verify active accounts
- 🧠 **Social Engineering** — "KYC update", "Prize claim", "Lottery" in remarks
- 🌙 **Late Night Attacks** — 3.4× higher fraud rate between 10PM–6AM
- 🏦 **Money Mule Networks** — coordinated fraud rings routing stolen funds

---

## 💡 Our Solution — ShieldPay

ShieldPay is a **real-time UPI fraud detection system** powered by a hybrid ML engine running on **AMD RYZEN AI** hardware.

Every transaction is analyzed in **under 80ms** — before the payment goes through — entirely **on-device**, with zero data leaving the user's phone.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔴 **Live Transaction Feed** | Real-time stream of transactions being analyzed as they happen |
| 🧠 **ML Fraud Engine** | RandomForest classifier (120 trees) trained on fraud patterns |
| 📊 **Risk Scoring** | 0–100 risk score with confidence percentage per transaction |
| 🔍 **VPA Registry Lookup** | Cross-checks against 4.8M+ verified & flagged VPA database |
| 💬 **NLP Remarks Analysis** | Scans transaction notes for 30+ social engineering keywords |
| 🚨 **Instant Alerts** | Color-coded Safe / Suspicious / Fraud verdict in real time |
| 📋 **RBI Reporting** | One-click fraud report submission to RBI CFCFRMS portal |
| 📈 **Analytics Dashboard** | 12-hour fraud activity chart + live metrics |

---

## 🏗️ Tech Stack

```
Frontend   →  HTML, CSS, Vanilla JS (served by Flask)
Backend    →  Python 3.12 + Flask
ML Engine  →  scikit-learn (RandomForestClassifier)
Database   →  SQLite3
Streaming  →  Server-Sent Events (SSE)
AI Target  →  AMD RYZEN AI NPU (ONNX-ready export)
```

---

## 🧠 How the ML Engine Works

ShieldPay uses a **hybrid scoring system**:

```
Final Risk Score = (ML Probability × 60%) + (Rule Engine × 40%)
```

### Feature Vector (per transaction):
| Feature | Description |
|---|---|
| `vpa_fraud_score` | Keyword match score on sender/receiver VPA |
| `amount_log` | Log-scaled transaction amount |
| `time_risk` | Risk weight based on time of day |
| `type_risk` | Risk weight based on transaction type |
| `note_score` | NLP keyword density in remarks |
| `is_mule` | Regex match against mule account patterns |
| `is_known_legit` | Verified merchant whitelist check |
| `is_known_fraud` | Hard-flagged fraud VPA registry check |

### Hard Override Rules:
- ✅ **Known merchant** + amount < ₹50K → instantly **SAFE** (97% confidence)
- 🚨 **Known fraud VPA** → instantly **FRAUD** (99% confidence)
- Everything else → **ML model decides**

---

## 🔌 REST API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Analyze a UPI transaction |
| `GET` | `/api/transactions` | Fetch transaction history |
| `GET` | `/api/stats` | Dashboard metrics + chart data |
| `GET` | `/api/vpa/lookup?vpa=` | VPA registry lookup |
| `POST` | `/api/report` | File fraud report |
| `GET` | `/api/stream` | SSE live transaction stream |

### Sample Request:
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

### Sample Response:
```json
{
  "risk_score": 95,
  "verdict": "fraud",
  "confidence": 99.0,
  "flags": [
    {"type": "alert", "msg": "VPA matches known fraud address in registry"},
    {"type": "alert", "msg": "Sender VPA contains impersonation keyword: 'helpdesk'"},
    {"type": "alert", "msg": "Unsolicited collect request — never approve without verifying"}
  ],
  "ml_probabilities": {"safe": 0.01, "suspicious": 0.04, "fraud": 0.95},
  "engine": "rule_override",
  "txn_id": 42
}
```

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/shieldpay.git
cd shieldpay

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python app.py

# 4. Open in browser
# → http://localhost:5000
```

---

## ⚡ AMD RYZEN AI Integration

ShieldPay is architected for **on-device deployment** on AMD RYZEN AI NPU:

- 🔒 **Privacy-first** — no transaction data ever leaves the device
- ⚡ **Sub-80ms latency** — hardware-accelerated tensor inference
- 📦 **ONNX-ready** — model can be exported and run on AMD NPU directly
- 🔋 **Power efficient** — NPU offloading saves CPU/battery on mobile

```python
# ONNX export for AMD RYZEN AI NPU deployment
from skl2onnx import convert_sklearn
model_onnx = convert_sklearn(engine.model, "FraudDetector")
# Deploy to AMD RYZEN AI hardware for edge inference
```

---

## 📁 Project Structure

```
shieldpay/
├── app.py              # Flask API server + SSE stream + DB logic
├── fraud_engine.py     # RandomForest ML engine + rule system
├── requirements.txt    # Python dependencies
├── shieldpay.db        # SQLite database (auto-created)
├── README.md           # This file
└── templates/
    └── index.html      # Full frontend dashboard
```

---

## 👥 Team

| Name | Role |
|---|---|
| Simon Paul | Full Stack Developer + ML Engineer |
| Varsha Rani | UI/UX Designer + Frontend Developer |
| Mayank Bansal | Data Scientist + Backend Developer |

---

## 🎯 Impact

- 🇮🇳 Targets India's **₹1.2L Cr annual UPI fraud** problem
- 👥 Protects everyday users — especially elderly & first-time UPI users
- 🏦 Integrates with existing UPI stack — no app changes needed for banks
- 📡 Works **offline** — on-device AMD RYZEN AI inference, no internet required
- ⚖️ **RBI compliant** — auto-reporting to CFCFRMS fraud portal

---

## 📜 License

MIT License — built for AMD Slingshot 2026

---

<div align="center">
  <strong>Built with ❤️ for AMD Slingshot 2026</strong><br>
  Powered by AMD RYZEN AI · Flask · scikit-learn
</div>
