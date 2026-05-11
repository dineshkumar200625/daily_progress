import os
import time
import requests
import threading
from flask import Flask, request, jsonify, abort
from functools import wraps

app = Flask(__name__)

LAST_ACTION_TIME = 0
last_action_lock = threading.Lock()

AI_API_KEY = os.getenv("AI_API_KEY")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
JENKINS_ROLLBACK_URL = os.getenv("JENKINS_ROLLBACK_URL")
JENKINS_SCALE_URL = os.getenv("JENKINS_SCALE_URL")
X_API_KEY = "mahesh-secure-key-2026"

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-API-KEY') == X_API_KEY:
            return f(*args, **kwargs)
        return abort(401)
    return decorated

def query_prometheus(query):
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query})
        results = response.json()['data']['result']
        return results
    except Exception:
        return []

def cooldown_active():
    with last_action_lock:
        return (time.time() - LAST_ACTION_TIME) < 300

def trigger_remediation(action_url):
    global LAST_ACTION_TIME
    try:
        requests.post(action_url, auth=(JENKINS_USER, JENKINS_API_TOKEN))
        with last_action_lock:
            LAST_ACTION_TIME = time.time()
        return True
    except Exception:
        return False

def ask_ai(metrics_report):
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{
            "role": "system", 
            "content": "You are an SRE. Respond with 'ROLLBACK', 'SCALE', or 'NONE'."
        }, {
            "role": "user", 
            "content": f"Analyze these metrics: {metrics_report}"
        }]
    }
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content']
    except Exception:
        return "NONE"

@app.route('/alert', methods=['POST'])
@require_api_key
def handle_alert():
    if cooldown_active():
        return jsonify({"status": "cooldown"}), 429
    
    alert_data = request.json
    decision = ask_ai(str(alert_data))
    
    if "ROLLBACK" in decision:
        trigger_remediation(JENKINS_ROLLBACK_URL)
    elif "SCALE" in decision:
        trigger_remediation(JENKINS_SCALE_URL)
        
    return jsonify({"decision": decision})

def monitor_loop():
    while True:
        if not cooldown_active():
            restarts = query_prometheus('sum(changes(kube_pod_container_status_restarts_total[5m]))')
            if restarts:
                ask_ai(f"Restarts detected: {restarts}")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
