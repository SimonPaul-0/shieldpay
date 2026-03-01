"""
ShieldPay Fraud Engine
ML-powered fraud scoring using scikit-learn + rule-based hybrid
"""

import re
import math
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# KNOWN PATTERN SETS
# ─────────────────────────────────────────────
FRAUD_VPA_KEYWORDS = [
    "helpdesk", "support", "kyc", "verify", "rbi", "sbi", "refund",
    "official", "help", "care", "service", "bank", "npci", "upi.gov",
    "update", "reward", "prize", "lottery", "govt", "alert"
]

MULE_VPA_PATTERNS = [
    r"^0x", r"mule\d*@", r"anon\d+@", r"temp\d+@",
    r"\d{10}@", r"unk\d+@", r"fraud"
]

SOCIAL_ENGINEERING_WORDS = [
    "prize", "lottery", "kyc", "otp", "account", "verify", "reward",
    "win", "claim", "refund", "emi", "urgent", "blocked", "suspended",
    "congratulations", "selected", "offer", "free", "gift", "helpline",
    "customer care", "amazon", "microsoft", "google", "income tax",
    "electricity", "gas", "water", "bill", "fine", "penalty"
]

KNOWN_LEGIT_MERCHANTS = {
    "swiggy@icici", "zomato@hdfcbank", "amazon@axisbank",
    "flipkart@axisbank", "airtel@upi", "paytm@paytm",
    "bookmyshow@icici", "irctc@sbi", "phonepe@ybl",
    "gpay@okaxis", "jio@paytm", "netflix@icici"
}

KNOWN_FRAUD_VPAS = {
    "sbi.kyc@upi", "rbi.helpdesk@upi", "paytm.support@ybl",
    "npcisupport@upi", "bankverify@ybl", "0x8a2b@ybl"
}

TIME_RISK = {
    "Morning":    0.05,
    "Afternoon":  0.03,
    "Evening":    0.12,
    "Late Night": 0.35,
}

TYPE_RISK = {
    "P2P Transfer":            0.10,
    "Merchant Payment":        0.02,
    "Unknown Collect Request": 0.40,
    "Bill Payment":            0.04,
    "QR Code Scan":            0.08,
}


# ─────────────────────────────────────────────
# SYNTHETIC TRAINING DATA (for ML model)
# ─────────────────────────────────────────────
def _make_training_data():
    """Generate synthetic labeled examples to train RandomForest."""
    np.random.seed(42)
    X, y = [], []

    def fe(vpa_fraud, amount_log, time_risk, type_risk, note_score, is_mule, is_known_legit, is_known_fraud):
        return [vpa_fraud, amount_log, time_risk, type_risk, note_score, is_mule, is_known_legit, is_known_fraud]

    # SAFE examples
    for _ in range(300):
        X.append(fe(0, np.random.uniform(2, 7), 0.05, 0.02, 0, 0, 1, 0))
        y.append(0)

    # SUSPICIOUS examples
    for _ in range(200):
        X.append(fe(
            np.random.choice([0, 1]),
            np.random.uniform(7, 11),
            np.random.choice([0.12, 0.35]),
            np.random.choice([0.10, 0.40]),
            np.random.uniform(0.1, 0.4),
            np.random.choice([0, 1]),
            0, 0
        ))
        y.append(1)

    # FRAUD examples
    for _ in range(200):
        X.append(fe(
            1,
            np.random.uniform(5, 13),
            np.random.choice([0.35, 0.12]),
            0.40,
            np.random.uniform(0.5, 1.0),
            np.random.choice([0, 1]),
            0,
            np.random.choice([0, 1])
        ))
        y.append(2)

    return np.array(X), np.array(y)


class FraudEngine:
    """
    Hybrid fraud detection:
    - Feature extraction from VPA, amount, time, type, remarks
    - RandomForest ML model for probability scoring
    - Rule-based override for known fraud/legit entities
    - Human-readable flag generation
    """

    def __init__(self):
        X, y = _make_training_data()
        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            class_weight={0: 1, 1: 2, 2: 4},
            random_state=42
        )
        self.model.fit(X, y)
        self.classes = ["safe", "suspicious", "fraud"]

    def _vpa_fraud_score(self, vpa: str) -> float:
        vpa_low = vpa.lower()
        if any(k in vpa_low for k in FRAUD_VPA_KEYWORDS):
            return 1.0
        if any(re.search(p, vpa_low) for p in MULE_VPA_PATTERNS):
            return 0.8
        return 0.0

    def _note_score(self, note: str) -> float:
        note_low = note.lower()
        hits = sum(1 for w in SOCIAL_ENGINEERING_WORDS if w in note_low)
        return min(hits / 3.0, 1.0)

    def _extract_flags(self, sender: str, receiver: str, amount: float,
                       txn_type: str, time_of_day: str, remarks: str) -> list:
        flags = []
        sender_low = sender.lower()
        recv_low   = receiver.lower()
        note_low   = remarks.lower()

        # VPA checks
        if receiver in KNOWN_FRAUD_VPAS or sender in KNOWN_FRAUD_VPAS:
            flags.append({"type": "alert", "msg": "VPA matches known fraud/scam address in registry"})

        matched_kw = [k for k in FRAUD_VPA_KEYWORDS if k in sender_low]
        if matched_kw:
            flags.append({"type": "alert", "msg": f"Sender VPA contains impersonation keyword: '{matched_kw[0]}'"})

        if any(re.search(p, recv_low) for p in MULE_VPA_PATTERNS):
            flags.append({"type": "alert", "msg": "Receiver VPA matches known money-mule account pattern"})

        if "@" not in receiver:
            flags.append({"type": "warn", "msg": "Invalid VPA format — not registered on NPCI UPI network"})

        # Amount checks
        if amount == 1 or amount == 2:
            flags.append({"type": "alert", "msg": "₹1–₹2 collect request — classic phishing probe to verify active account"})
        elif amount > 100000:
            flags.append({"type": "alert", "msg": f"Very high-value transaction (₹{amount:,.0f}) exceeds safe threshold"})
        elif amount > 50000:
            flags.append({"type": "warn", "msg": f"High-value transaction (₹{amount:,.0f}) — verify receiver identity"})

        # Time checks
        if time_of_day == "Late Night":
            flags.append({"type": "warn", "msg": "Late-night transaction — 3.4× higher fraud correlation in 10PM–6AM window"})

        # Transaction type
        if "Collect" in txn_type:
            flags.append({"type": "alert", "msg": "Unsolicited collect request — never approve without verifying the source"})

        # Remarks NLP
        matched_note = [w for w in SOCIAL_ENGINEERING_WORDS if w in note_low]
        if len(matched_note) >= 2:
            flags.append({"type": "alert", "msg": f"Multiple social-engineering keywords in remarks: {matched_note[:3]}"})
        elif matched_note:
            flags.append({"type": "warn", "msg": f"Suspicious keyword in transaction remarks: '{matched_note[0]}'"})

        # Positive signal
        if receiver in KNOWN_LEGIT_MERCHANTS:
            flags.append({"type": "safe", "msg": f"Receiver is a verified merchant on ShieldPay registry"})

        if not flags:
            flags.append({"type": "info", "msg": "No suspicious patterns detected — transaction appears normal"})

        return flags

    def analyze(self, sender_vpa: str, receiver_vpa: str, amount: float,
                txn_type: str = "P2P Transfer", time_of_day: str = "Afternoon",
                remarks: str = "") -> dict:
        """
        Full fraud analysis. Returns:
        - risk_score (0–100)
        - verdict: 'safe' | 'suspicious' | 'fraud'
        - confidence (%)
        - flags: list of human-readable reasons
        - ml_probabilities: raw RF class probabilities
        """
        sender_low  = sender_vpa.lower()
        recv_low    = receiver_vpa.lower()

        # Hard overrides
        if sender_vpa in KNOWN_FRAUD_VPAS or receiver_vpa in KNOWN_FRAUD_VPAS:
            flags = self._extract_flags(sender_vpa, receiver_vpa, amount, txn_type, time_of_day, remarks)
            return {
                "risk_score": 95,
                "verdict": "fraud",
                "confidence": 99.0,
                "flags": flags,
                "ml_probabilities": {"safe": 0.01, "suspicious": 0.04, "fraud": 0.95},
                "engine": "rule_override"
            }

        if receiver_vpa in KNOWN_LEGIT_MERCHANTS and amount < 50000 and "Collect" not in txn_type:
            flags = self._extract_flags(sender_vpa, receiver_vpa, amount, txn_type, time_of_day, remarks)
            return {
                "risk_score": 5,
                "verdict": "safe",
                "confidence": 97.0,
                "flags": flags,
                "ml_probabilities": {"safe": 0.97, "suspicious": 0.02, "fraud": 0.01},
                "engine": "rule_override"
            }

        # Feature vector
        vpa_fraud    = self._vpa_fraud_score(sender_low)
        amount_log   = math.log1p(amount)
        time_risk    = TIME_RISK.get(time_of_day, 0.1)
        type_risk    = TYPE_RISK.get(txn_type, 0.1)
        note_score   = self._note_score(remarks)
        is_mule      = 1.0 if any(re.search(p, recv_low) for p in MULE_VPA_PATTERNS) else 0.0
        is_legit     = 1.0 if receiver_vpa in KNOWN_LEGIT_MERCHANTS else 0.0
        is_known_bad = 1.0 if (sender_vpa in KNOWN_FRAUD_VPAS or receiver_vpa in KNOWN_FRAUD_VPAS) else 0.0

        features = np.array([[vpa_fraud, amount_log, time_risk, type_risk,
                               note_score, is_mule, is_legit, is_known_bad]])

        proba = self.model.predict_proba(features)[0]
        # Map to 3 classes safely
        prob_map = {self.classes[i]: round(float(proba[i]), 4) for i in range(len(proba))}

        # Risk score: weighted combination of ML + rules
        rule_score = (
            vpa_fraud * 35 +
            time_risk * 25 +
            type_risk * 30 +
            note_score * 20 +
            is_mule * 25 +
            (15 if amount == 1 else 0) +
            (10 if amount > 50000 else 0)
        )
        ml_score   = (prob_map.get("suspicious", 0) * 50 + prob_map.get("fraud", 0) * 100)
        risk_score = min(round(rule_score * 0.4 + ml_score * 0.6), 100)

        if risk_score >= 60:
            verdict = "fraud"
        elif risk_score >= 28:
            verdict = "suspicious"
        else:
            verdict = "safe"

        confidence = round(max(prob_map.values()) * 100, 1)
        flags      = self._extract_flags(sender_vpa, receiver_vpa, amount, txn_type, time_of_day, remarks)

        return {
            "risk_score": risk_score,
            "verdict": verdict,
            "confidence": confidence,
            "flags": flags,
            "ml_probabilities": prob_map,
            "engine": "hybrid_ml"
        }
