"""
Autonomous SRE Agent for EKS
"""

import os
import time
import requests
import threading
import logging
from flask import Flask, request, jsonify, abort
from functools import wraps
from groq import Groq

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class BaseRemediationProvider:
    def execute(self, action): pass

class JenkinsProvider(BaseRemediationProvider):
    def execute(self, action_url):
        return trigger_remediation(action_url, "Jenkins")

class CostAwareEvaluator:
    def is_cost_effective(self, action):
        return not cooldown_active()

class PredictiveEngine:
    def __init__(self):
        self.metric_history = []
    
    def forecast_anomaly(self, metrics):
        if len(self.metric_history) > 10:
            avg_restarts = sum(m.get('restarts', 0) for m in self.metric_history[-5:]) / 5
            if metrics.get('restarts', 0) > avg_restarts * 2:
                return True
        self.metric_history.append(metrics)
        return False

LAST_ACTION_TIME = 0
last_action_lock = threading.Lock()
predictive_engine = PredictiveEngine()

AI_API_KEY = os.getenv("AI_API_KEY")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
JENKINS_ROLLBACK_URL = os.getenv("JENKINS_ROLLBACK_URL")
JENKINS_SCALE_URL = os.getenv("JENKINS_SCALE_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
X_API_KEY = os.getenv("X_API_KEY")

groq_client = Groq(api_key=AI_API_KEY) if AI_API_KEY else None

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not X_API_KEY:
            abort(503)
        if request.headers.get('X-API-KEY') == X_API_KEY:
            return f(*args, **kwargs)
        abort(401)
    return decorated

def send_slack(message):
    if SLACK_WEBHOOK_URL:
        try:
            requests.post(SLACK_WEBHOOK_URL, json={"text": f"🤖 *SRE Agent:* {message}"}, timeout=5)
        except requests.exceptions.RequestException:
            pass

def query_prometheus(query):
    if not PROMETHEUS_URL:
        return []
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query}, timeout=10)
        response.raise_for_status()
        return response.json().get('data', {}).get('result', [])
    except requests.exceptions.RequestException:
        return []

def cooldown_active():
    with last_action_lock:
        return (time.time() - LAST_ACTION_TIME) < 300

def trigger_remediation(action_url, name):
    global LAST_ACTION_TIME
    if cooldown_active():
        return False
    try:
        if not JENKINS_USER or not JENKINS_API_TOKEN:
            return False
        response = requests.post(action_url, auth=(JENKINS_USER, JENKINS_API_TOKEN), timeout=30)
        response.raise_for_status()
        with last_action_lock:
            LAST_ACTION_TIME = time.time()
        send_slack(f"✅ Successful Remediation: {name}")
        return True
    except requests.exceptions.RequestException:
        return False

def ask_ai(report):
    if not groq_client:
        return "NONE"
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "SRE Expert. Respond ONLY: ROLLBACK, SCALE, NONE."},
                {"role": "user", "content": report[:4000]}
            ],
            temperature=0.1,
            max_tokens=20
        )
        return completion.choices[0].message.content.upper()
    except Exception:
        return "NONE"

def run_remediation_cycle(metrics_data):
    if cooldown_active():
        return
    
    if predictive_engine.forecast_anomaly(metrics_data):
        send_slack("⚠️ Anomaly forecasted, taking proactive action")
    
    decision = ask_ai(str(metrics_data))
    
    if "ROLLBACK" in decision:
        trigger_remediation(JENKINS_ROLLBACK_URL, "Rollback")
    elif "SCALE" in decision:
        trigger_remediation(JENKINS_SCALE_URL, "Scale Up")

@app.route('/slack/command', methods=['POST'])
def slack_command():
    command = request.form.get('command')
    
    if command == '/sre-status':
        with last_action_lock:
            last_action = LAST_ACTION_TIME
        return jsonify({
            "text": f"Last action: {time.ctime(last_action) if last_action else 'Never'}"
        })
    elif command == '/sre-health':
        return jsonify({"text": "✅ Operational"})
    else:
        return jsonify({"text": "Unknown command"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "alive",
        "groq_ready": groq_client is not None
    })

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
            try:
                restarts = query_prometheus('sum(changes(kube_pod_container_status_restarts_total[5m]))')
                cpu = query_prometheus('avg(rate(container_cpu_usage_seconds_total[5m])) by (pod)')
                mem = query_prometheus('avg(container_memory_working_set_bytes) by (pod)')
                
                metrics_summary = {
                    'restarts': len(restarts),
                    'cpu_pods': len(cpu),
                    'mem_pods': len(mem),
                    'timestamp': time.time()
                }
                run_remediation_cycle(metrics_summary)
            except Exception as e:
                logging.error(f"Monitor loop error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
