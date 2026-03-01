"""
ShieldPay Backend — UPI Fraud Detection API
Flask + scikit-learn + SQLite
AMD Slingshot 2026
"""

import sqlite3
import json
import random
import time
import threading
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, Response
from fraud_engine import FraudEngine

app = Flask(__name__)
engine = FraudEngine()

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
DB_PATH = "shieldpay.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_vpa  TEXT NOT NULL,
            receiver_vpa TEXT NOT NULL,
            amount      REAL NOT NULL,
            txn_type    TEXT,
            time_of_day TEXT,
            remarks     TEXT,
            risk_score  REAL,
            verdict     TEXT,
            flags       TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fraud_reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id      INTEGER REFERENCES transactions(id),
            reporter    TEXT,
            description TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vpa_registry (
            vpa         TEXT PRIMARY KEY,
            entity_name TEXT,
            verified    INTEGER DEFAULT 0,
            fraud_count INTEGER DEFAULT 0
        );
    """)
    # Seed VPA registry with known entities
    known_vpas = [
        ("swiggy@icici",       "Swiggy India Pvt Ltd",       1, 0),
        ("zomato@hdfcbank",    "Zomato Ltd",                  1, 0),
        ("amazon@axisbank",    "Amazon Seller Services",      1, 0),
        ("flipkart@axisbank",  "Flipkart Internet Pvt Ltd",   1, 0),
        ("airtel@upi",         "Bharti Airtel Ltd",           1, 0),
        ("paytm@paytm",        "One97 Communications",        1, 0),
        ("sbi.kyc@upi",        "UNKNOWN — Impersonation",     0, 147),
        ("rbi.helpdesk@upi",   "UNKNOWN — Impersonation",     0, 312),
        ("paytm.support@ybl",  "UNKNOWN — Impersonation",     0, 89),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO vpa_registry VALUES (?,?,?,?)", known_vpas
    )
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
# SIMULATE BACKGROUND TRANSACTIONS
# ─────────────────────────────────────────────
SIMULATED_TXNS = [
    {"sender":"rohit@paytm",      "receiver":"swiggy@icici",       "amount":249,    "type":"Merchant Payment",        "time":"Morning",    "remarks":"food order"},
    {"sender":"priya@gpay",       "receiver":"flipkart@axisbank",  "amount":1200,   "type":"Merchant Payment",        "time":"Afternoon",  "remarks":"shopping"},
    {"sender":"sbi.kyc@upi",      "receiver":"0x8a2b@ybl",         "amount":9999,   "type":"Unknown Collect Request", "time":"Late Night", "remarks":"kyc update urgent"},
    {"sender":"unknown@okicici",  "receiver":"mule1@paytm",        "amount":50000,  "type":"P2P Transfer",            "time":"Late Night", "remarks":"prize claim"},
    {"sender":"arun@phonepe",     "receiver":"zomato@hdfcbank",    "amount":500,    "type":"Merchant Payment",        "time":"Evening",    "remarks":"dinner"},
    {"sender":"rbi.helpdesk@upi", "receiver":"scam9@ybl",          "amount":200000, "type":"Unknown Collect Request", "time":"Late Night", "remarks":"account verify refund"},
    {"sender":"anon99@upi",       "receiver":"newvpa@axisbank",    "amount":15000,  "type":"P2P Transfer",            "time":"Late Night", "remarks":"lottery win claim"},
    {"sender":"meera@gpay",       "receiver":"amazon@axisbank",    "amount":850,    "type":"Merchant Payment",        "time":"Afternoon",  "remarks":"books"},
    {"sender":"karan@phonepe",    "receiver":"airtel@upi",         "amount":3200,   "type":"Bill Payment",            "time":"Morning",    "remarks":"bill pay"},
    {"sender":"paytm.support@ybl","receiver":"unk3@okaxis",        "amount":75000,  "type":"Unknown Collect Request", "time":"Late Night", "remarks":"refund process otp"},
    {"sender":"neha@ibl",         "receiver":"bookmyshow@icici",   "amount":1800,   "type":"Merchant Payment",        "time":"Afternoon",  "remarks":"movie tickets"},
    {"sender":"rajesh@ybl",       "receiver":"1ruppee.collect@upi","amount":1,      "type":"Unknown Collect Request", "time":"Evening",    "remarks":"verification"},
]

def background_simulator():
    """Continuously insert simulated transactions into DB."""
    i = 0
    while True:
        t = SIMULATED_TXNS[i % len(SIMULATED_TXNS)]
        result = engine.analyze(
            t["sender"], t["receiver"], t["amount"],
            t["type"], t["time"], t["remarks"]
        )
        conn = get_db()
        conn.execute("""
            INSERT INTO transactions
            (sender_vpa, receiver_vpa, amount, txn_type, time_of_day, remarks, risk_score, verdict, flags)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            t["sender"], t["receiver"], t["amount"],
            t["type"], t["time"], t["remarks"],
            result["risk_score"], result["verdict"],
            json.dumps(result["flags"])
        ))
        conn.commit()
        conn.close()
        i += 1
        time.sleep(random.uniform(1.5, 3.5))

sim_thread = threading.Thread(target=background_simulator, daemon=True)
sim_thread.start()

# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Analyze a single transaction and store result."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload"}), 400

    required = ["sender_vpa", "receiver_vpa", "amount"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    result = engine.analyze(
        sender_vpa   = data.get("sender_vpa", ""),
        receiver_vpa = data.get("receiver_vpa", ""),
        amount       = float(data.get("amount", 0)),
        txn_type     = data.get("txn_type", "P2P Transfer"),
        time_of_day  = data.get("time_of_day", "Afternoon"),
        remarks      = data.get("remarks", ""),
    )

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO transactions
        (sender_vpa, receiver_vpa, amount, txn_type, time_of_day, remarks, risk_score, verdict, flags)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data["sender_vpa"], data["receiver_vpa"], float(data["amount"]),
        data.get("txn_type"), data.get("time_of_day"), data.get("remarks"),
        result["risk_score"], result["verdict"], json.dumps(result["flags"])
    ))
    txn_id = cur.lastrowid
    conn.commit()
    conn.close()

    result["txn_id"] = txn_id
    return jsonify(result)


@app.route("/api/transactions", methods=["GET"])
def transactions():
    """Return recent transactions with filters."""
    limit   = min(int(request.args.get("limit", 50)), 200)
    verdict = request.args.get("verdict")  # safe | suspicious | fraud

    conn = get_db()
    if verdict:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE verdict=? ORDER BY created_at DESC LIMIT ?",
            (verdict, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        d["flags"] = json.loads(d["flags"] or "[]")
        out.append(d)
    return jsonify(out)


@app.route("/api/stats", methods=["GET"])
def stats():
    """Aggregated stats for the dashboard."""
    conn = get_db()
    total      = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    fraud_cnt  = conn.execute("SELECT COUNT(*) FROM transactions WHERE verdict='fraud'").fetchone()[0]
    susp_cnt   = conn.execute("SELECT COUNT(*) FROM transactions WHERE verdict='suspicious'").fetchone()[0]
    saved_amt  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE verdict='fraud'").fetchone()[0]
    avg_score  = conn.execute("SELECT COALESCE(AVG(risk_score),0) FROM transactions").fetchone()[0]

    # hourly breakdown for chart (last 12 hours)
    hourly = []
    for h in range(11, -1, -1):
        ts_from = (datetime.now() - timedelta(hours=h+1)).strftime("%Y-%m-%d %H:%M:%S")
        ts_to   = (datetime.now() - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")
        cnt = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE verdict IN ('fraud','suspicious') AND created_at BETWEEN ? AND ?",
            (ts_from, ts_to)
        ).fetchone()[0]
        label = (datetime.now() - timedelta(hours=h)).strftime("%H:00")
        hourly.append({"label": label, "count": cnt})

    conn.close()
    return jsonify({
        "total_scanned": total,
        "fraud_blocked": fraud_cnt,
        "suspicious_flagged": susp_cnt,
        "amount_protected": round(saved_amt),
        "avg_risk_score": round(avg_score, 1),
        "hourly_chart": hourly,
    })


@app.route("/api/vpa/lookup", methods=["GET"])
def vpa_lookup():
    """Check a VPA against the registry."""
    vpa = request.args.get("vpa", "").strip().lower()
    if not vpa:
        return jsonify({"error": "vpa param required"}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM vpa_registry WHERE LOWER(vpa)=?", (vpa,)
    ).fetchone()
    conn.close()

    if row:
        return jsonify({
            "vpa": row["vpa"],
            "entity_name": row["entity_name"],
            "verified": bool(row["verified"]),
            "fraud_count": row["fraud_count"],
            "status": "verified" if row["verified"] else "flagged"
        })
    return jsonify({"vpa": vpa, "verified": False, "status": "unknown", "entity_name": None, "fraud_count": 0})


@app.route("/api/report", methods=["POST"])
def report_fraud():
    """Submit a fraud report for a transaction."""
    data = request.get_json()
    txn_id = data.get("txn_id")
    reporter = data.get("reporter", "anonymous")
    description = data.get("description", "")

    if not txn_id:
        return jsonify({"error": "txn_id required"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO fraud_reports (txn_id, reporter, description) VALUES (?,?,?)",
        (txn_id, reporter, description)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Fraud report submitted to RBI CFCFRMS"})


@app.route("/api/stream")
def stream():
    """SSE stream: push latest transaction as it arrives."""
    def event_gen():
        last_id = 0
        while True:
            conn = get_db()
            rows = conn.execute(
                "SELECT * FROM transactions WHERE id > ? ORDER BY id ASC LIMIT 5",
                (last_id,)
            ).fetchall()
            conn.close()
            for row in rows:
                d = dict(row)
                d["flags"] = json.loads(d["flags"] or "[]")
                last_id = d["id"]
                yield f"data: {json.dumps(d)}\n\n"
            time.sleep(1)
    return Response(event_gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print("\n🛡️  ShieldPay API running at http://localhost:5000\n")
    app.run(debug=True, port=5000, threaded=True)
