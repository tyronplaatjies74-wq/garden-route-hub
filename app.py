from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os

app = Flask(__name__)
CORS(app)

# Use env var first, fallback to hardcoded so it still works
SPECIALIST_BASE = os.environ.get("SPECIALIST_URL", "https://garden-route-specialist-api.vercel.app").rstrip("/")
SPECIALIST_PLAN_URL = f"{SPECIALIST_BASE}/api/plan"
SPECIALIST_CHAT_URL = f"{SPECIALIST_BASE}/api/chat"

def call_specialist(url, payload, timeout=25):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        # Return EVERYTHING, even errors, so we can debug
        try:
            body = r.json()
        except:
            body = {"raw": r.text[:500]}
        return {"status": r.status_code, "body": body}
    except Exception as e:
        return {"status": 0, "body": {"error": str(e)}}

def parse_query(q):
    q = (q or "").lower()
    towns = ["knysna", "plett", "plettenberg", "george", "wilderness", "sedgefield", "oudtshoorn", "mossel bay", "hermanus", "tsitsikamma", "nature's valley", "rheenendal"]
    town = "Knysna"
    for t in towns:
        if t in q:
            town = t.title()
            break
    m = re.search(r"(\d+)\s*day", q)
    days = int(m.group(1)) if m else 2
    return town, days

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "specialist_url": SPECIALIST_BASE, "specialist_plan_url": SPECIALIST_PLAN_URL})

@app.route("/api/plan", methods=["POST", "OPTIONS"])
def plan():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or {}
    # Accept ALL frontend formats: {query} OR {town, days} OR {message}
    query = data.get("query") or data.get("message") or data.get("prompt") or ""
    town = data.get("town")
    days = data.get("days", 2)
    if not town:
        town, days = parse_query(query if query else f"{town} {days} days")
    if isinstance(days, str):
        try: days = int(days)
        except: days = 2

    result = call_specialist(SPECIALIST_PLAN_URL, {"town": town, "days": days, "query": query})

    if result["status"] == 200:
        return jsonify({"source": "hub -> specialist", "town": town, "days": days, "plan": result["body"], "events": [], "restaurants": []})

    # NOW you will actually see WHY it failed
    return jsonify({"error": "Specialist failed", "specialist_status": result["status"], "specialist_body": result["body"], "tried_url": SPECIALIST_PLAN_URL, "town": town, "days": days}), 502

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    # This was missing - this is what Garden Route AI calls
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or {}
    query = data.get("query") or data.get("message") or data.get("prompt") or ""
    # If it's a plan request, route to plan logic
    if any(w in query.lower() for w in ["plan", "itinerary", "days in", "day in"]):
        return plan()
    # Otherwise forward to Specialist chat if it has it, else fallback to plan
    result = call_specialist(SPECIALIST_CHAT_URL, {"query": query, "message": query})
    if result["status"] == 200:
        return jsonify(result["body"])
    # Fallback: try plan endpoint
    return plan()

@app.route("/api/search", methods=["POST", "OPTIONS"])
def search():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})
    data = request.get_json(silent=True) or {}
    query = data.get("query", "") or data.get("message", "")
    town, days = parse_query(query)
    if any(w in query.lower() for w in ["plan", "itinerary", "days in"]):
        return plan()
    return jsonify({"source": "hub", "town": town, "days": days, "type": "events", "message": f"Search local events for {town}"})

if __name__ == "__main__":
    app.run()