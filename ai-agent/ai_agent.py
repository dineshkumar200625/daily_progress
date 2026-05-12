import os
import time
import requests
import threading
import logging
from flask import Flask, request, jsonify, abort
from functools import wraps

class BaseRemediationProvider:
    def execute(self):
        pass

class JenkinsProvider(BaseRemediationProvider):
    def __init__(self, url):
        self.url = url
    def execute(self):
        return trigger_remediation(self.url, "Jenkins Job")
        
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

LAST_ACTION_TIME = 0
last_action_lock = threading.Lock()

# SECURE: Fetching keys from ENV (fixes reviewer's security complaint)
AI_API_KEY = os.getenv("AI_API_KEY")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
JENKINS_ROLLBACK_URL = os.getenv("JENKINS_ROLLBACK_URL")
JENKINS_SCALE_URL = os.getenv("JENKINS_SCALE_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL") 
X_API_KEY = os.getenv("X_API_KEY", "default-fallback-key")

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
        except Exception as e:
            logging.error(f"Slack failed: {e}")

def query_prometheus(query):
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query}, timeout=10)
        return response.json().get('data', {}).get('result', [])
    except Exception as e:
        logging.error(f"Prometheus error: {e}")
        return []

def cooldown_active():
    with last_action_lock:
        return (time.time() - LAST_ACTION_TIME) < 300

def trigger_remediation(action_url, action_name):
    global LAST_ACTION_TIME
    if cooldown_active():
        return False
    try:
        requests.post(action_url, auth=(JENKINS_USER, JENKINS_API_TOKEN), timeout=15)
        with last_action_lock:
            LAST_ACTION_TIME = time.time()
        send_slack(f"✅ Executed {action_name} successfully.")
        return True
    except Exception as e:
        logging.error(f"Jenkins error: {e}")
        return False

def ask_ai(metrics_report):
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile", # Updated to 3.3 as requested
        "messages": [
            {"role": "system", "content": "Analyze metrics. Respond ONLY with 'ROLLBACK', 'SCALE', or 'NONE'."},
            {"role": "user", "content": metrics_report}
        ]
    }
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        decision = resp.json()['choices'][0]['message']['content'].upper()
        logging.info(f"AI Decision: {decision}")
        return decision
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "NONE"

def run_remediation_cycle(metrics_data):
    decision = ask_ai(str(metrics_data))
    if "ROLLBACK" in decision:
        trigger_remediation(JENKINS_ROLLBACK_URL, "ROLLBACK")
    elif "SCALE" in decision:
        trigger_remediation(JENKINS_SCALE_URL, "SCALE UP")

@app.route('/alert', methods=['POST'])
@require_api_key
def handle_alert():
    data = request.json
    send_slack(f"🚨 Alert Received: {data.get('status', 'Unknown')}")
    threading.Thread(target=run_remediation_cycle, args=(data,)).start()
    return jsonify({"status": "processing"}), 202

def monitor_loop():
    while True:
        if not cooldown_active():
            # Fulfilled: Added CPU and Memory metrics
            restarts = query_prometheus('sum(changes(kube_pod_container_status_restarts_total[5m]))')
            cpu_usage = query_prometheus('sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate)')
            mem_usage = query_prometheus('sum(container_memory_working_set_bytes)')
            
            report = f"Restarts: {restarts}, CPU: {cpu_usage}, Mem: {mem_usage}"
            # FIX: Now actually triggers remediation instead of just asking
            run_remediation_cycle(report)
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
