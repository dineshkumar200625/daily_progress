import os
import time
import requests
import threading
import logging
from flask import Flask, request, jsonify, abort
from functools import wraps

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class RemediationProvider:
    def execute(self, action): pass

class JenkinsProvider(RemediationProvider):
    def execute(self, action_url):
        return trigger_remediation(action_url, "Jenkins")

class CostAwareEvaluator:
    def is_cost_effective(self, action):
        return True

class PredictiveEngine:
    def forecast_anomaly(self, metrics):
        return False 

LAST_ACTION_TIME = 0
last_action_lock = threading.Lock()

AI_API_KEY = os.getenv("AI_API_KEY")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
JENKINS_ROLLBACK_URL = os.getenv("JENKINS_ROLLBACK_URL")
JENKINS_SCALE_URL = os.getenv("JENKINS_SCALE_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
X_API_KEY = os.getenv("X_API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get('X-API-KEY') == X_API_KEY:
            return f(*args, **kwargs)
        return abort(401)
    return decorated

def send_slack(message):
    if SLACK_WEBHOOK_URL:
        try:
            requests.post(SLACK_WEBHOOK_URL, json={"text": f"🤖 *SRE Agent:* {message}"})
        except Exception: pass

def query_prometheus(query):
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query}, timeout=10)
        return response.json().get('data', {}).get('result', [])
    except Exception: return []

def cooldown_active():
    with last_action_lock:
        return (time.time() - LAST_ACTION_TIME) < 300

def trigger_remediation(action_url, name):
    global LAST_ACTION_TIME
    if cooldown_active(): return False
    try:
        requests.post(action_url, auth=(JENKINS_USER, JENKINS_API_TOKEN))
        with last_action_lock:
            LAST_ACTION_TIME = time.time()
        send_slack(f"✅ Successful Remediation: {name}")
        return True
    except Exception: return False

def ask_ai(report):
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "SRE Expert. Respond ONLY: ROLLBACK, SCALE, NONE."},
            {"role": "user", "content": report}
        ]
    }
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        return resp.json()['choices'][0]['message']['content'].upper()
    except Exception: return "NONE"

def run_remediation_cycle(metrics):
    if CostAwareEvaluator().is_cost_effective("REMEDIATE"):
        decision = ask_ai(str(metrics))
        if "ROLLBACK" in decision:
            trigger_remediation(JENKINS_ROLLBACK_URL, "Rollback")
        elif "SCALE" in decision:
            trigger_remediation(JENKINS_SCALE_URL, "Scale Up")

@app.route('/alert', methods=['POST'])
@require_api_key
def handle_alert():
    data = request.json
    send_slack(f"🚨 Incoming Alert: {data}")
    threading.Thread(target=run_remediation_cycle, args=(data,)).start()
    return jsonify({"status": "processing"}), 202

def monitor_loop():
    while True:
        if not cooldown_active():
            restarts = query_prometheus('sum(changes(kube_pod_container_status_restarts_total[5m]))')
            cpu = query_prometheus('sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate)')
            mem = query_prometheus('sum(container_memory_working_set_bytes)')
            
            run_remediation_cycle(f"Restarts: {restarts}, CPU: {cpu}, Mem: {mem}")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
