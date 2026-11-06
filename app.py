from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re

app = Flask(__name__)
CORS(app)

# --- REGISTRY: All your scrapers / plug-ins talk to Hub, Hub talks to them ---
# Add new plug-ins here, frontend never needs to change
PLUGINS = {
    "specialist": "https://garden-route-specialist-api.vercel.app/api/plan",
    # When you have separate scrapers, add them here:
    # "events": "https://your-events-scraper.vercel.app/api/events",
    # "restaurants": "https://your-restaurants-scraper.vercel.app/api/restaurants",
    # "weather": "https://your-weather-plugin.vercel.app/api/weather",
}

def call_plugin(name, payload, timeout=15):
    url = PLUGINS.get(name)
    if not url:
        return None
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Plugin {name} failed: {e}")
    return None

def parse_query(q):
    q = q.lower()
    # Find town
    towns = ["knysna", "plett", "plettenberg", "george", "wilderness", "sedgefield", "oudtshoorn", "mossel bay", "hermanus", "tsitsikamma", "nature's valley", "rheenendal"]
    town = "Knysna"
    for t in towns:
        if t in q:
            town = t.title()
            break
    # Find days - "2 days", "3 day"
    m = re.search(r"(\d+)\s*day", q)
    days = int(m.group(1)) if m else 2
    return town, days

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "plugins": list(PLUGINS.keys())})

@app.route("/api/plan", methods=["POST"])
def plan():
    data = request.get_json() or {}
    query = data.get("query", "") or data.get("town", "")
    town = data.get("town")
    days = data.get("days", 2)

    if not town and query:
        town, days = parse_query(query)

    # 1. Ask Specialist for the plan
    specialist_result = call_plugin("specialist", {"town": town, "days": days})

    # 2. Later: also ask events / restaurants and combine here
    # events = call_plugin("events", {"town": town, "days": days})

    if specialist_result:
        return jsonify({
            "source": "hub -> specialist",
            "town": town,
            "days": days,
            "plan": specialist_result,
            "events": [],
            "restaurants": []
        })

    return jsonify({"error": "Specialist offline", "town": town, "days": days}), 503

@app.route("/api/search", methods=["POST"])
def search():
    # This is the ONE endpoint your frontend will use for everything
    data = request.get_json() or {}
    query = data.get("query", "")
    town, days = parse_query(query)

    # If user wants a plan, route to Specialist
    if "plan" in query.lower() or "itinerary" in query.lower() or "days in" in query.lower():
        return plan()

    # Otherwise, just return town info for now - frontend uses local data
    return jsonify({
        "source": "hub",
        "town": town,
        "days": days,
        "type": "events",
        "message": f"Search local events for {town}"
    })

if __name__ == "__main__":
    app.run()