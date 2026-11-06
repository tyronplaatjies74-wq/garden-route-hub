import os, requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
SPECIALIST_URL = os.environ.get("SPECIALIST_URL", "").rstrip("/")

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garden Route Hub</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:20px auto;padding:10px">
<h2>Garden Route Hub</h2>
<div id="chat" style="border:1px solid #ccc;height:300px;overflow:auto;padding:10px"></div>
<input id="msg" style="width:75%;padding:10px" placeholder="Ask about Garden Route...">
<button onclick="send()" style="padding:10px">Send</button>
<script>
async function send(){
  let m=document.getElementById('msg').value;
  if(!m) return;
  document.getElementById('chat').innerHTML+='<p><b>You:</b> '+m+'</p>';
  document.getElementById('msg').value='';
  let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
  let d=await r.json();
  document.getElementById('chat').innerHTML+='<p><b>Hub:</b> '+(d.reply||d.error||'No reply')+'</p>';
}
</script></body></html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("message", "")
    if not SPECIALIST_URL:
        return jsonify({"error": "SPECIALIST_URL not set"}), 500
    try:
        r = requests.post(f"{SPECIALIST_URL}/api/plan", json={"message": msg}, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()