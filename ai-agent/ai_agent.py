import os
import threading
import json
import time
import logging
from typing import Dict, Any
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://monitoring-stack-kube-prom-prometheus.observability.svc.cluster.local:9090/api/v1/query")
AI_API_URL = os.getenv("AI_API_URL", "https://api.groq.com/openai/v1/chat/completions")
AI_API_KEY = os.getenv("AI_API_KEY")
JENKINS_ROLLBACK_URL = os.getenv("JENKINS_ROLLBACK_URL","http://my-jenkins.jenkins.svc.cluster.local:8080/job/Rollback-Pipeline/build?token=sre-token")
JENKINS_SCALE_URL = os.getenv("JENKINS_SCALE_URL","http://my-jenkins.jenkins.svc.cluster.local:8080/job/Scale-Pipeline/build?token=sre-token")
JENKINS_USER = os.getenv("JENKINS_USER","admin")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
NOTIFICATION_WEBHOOK = os.getenv("NOTIFICATION_WEBHOOK")

LAST_ACTION_TIME = 0
COOLDOWN_SECONDS = 300
session = requests.Session()

def query_prometheus(query: str) -> float:
    try:
        response = session.get(PROMETHEUS_URL, params={"query": query}, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get("data", {}).get("result", [])
        if not result:
            return 0.0
        value = float(result[0]["value"][1])
        return round(value, 2)
    except Exception as e:
        logger.error(f"Prometheus query failed: {e}")
        return 0.0

def get_metrics() -> Dict[str, Any]:
    cpu_query = "sum(rate(container_cpu_usage_seconds_total[2m])) * 100"
    memory_query = "(sum(container_memory_usage_bytes) / sum(machine_memory_bytes)) * 100"
    restart_query = "sum(kube_pod_container_status_restarts_total)"
    
    metrics = {
        "cpu_percent": query_prometheus(cpu_query),
        "memory_percent": query_prometheus(memory_query),
        "restart_count": query_prometheus(restart_query)
    }
    logger.info(f"Metrics: {metrics}")
    return metrics

def send_notification(action: str, reason: str):
    if not NOTIFICATION_WEBHOOK:
        return
    payload = {"text": f"⚠️ SRE AGENT ACTION ⚠️\n*Action:* {action}\n*Reason:* {reason}"}
    try:
        session.post(NOTIFICATION_WEBHOOK, json=payload, timeout=10).raise_for_status()
    except Exception as e:
        logger.error(f"Notification failed: {e}")

def ask_ai(metrics: Dict[str, Any]) -> Dict[str, str]:
    prompt = f"""
    Analyze K8s metrics: CPU: {metrics['cpu_percent']}%, Mem: {metrics['memory_percent']}%, Restarts: {metrics['restart_count']}.
    Rules: High CPU/Low Restarts = SCALE | High Restarts = ROLLBACK | Stable = OBSERVE.
    Return ONLY JSON: {{"action": "SCALE|ROLLBACK|OBSERVE", "reason": "string"}}
    """
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        response = session.post(AI_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        decision = json.loads(response.json()["choices"][0]["message"]["content"])
        action = decision.get("action", "OBSERVE").upper()
        return {"action": action if action in ["SCALE", "ROLLBACK", "OBSERVE"] else "OBSERVE", "reason": decision.get("reason", "")}
    except Exception as e:
        logger.error(f"AI failed: {e}")
        return {"action": "OBSERVE", "reason": "AI Error"}

def trigger_jenkins_job(url: str, action: str):
    if not url:
        logger.error(f"Jenkins URL for {action} not configured")
        return
    try:
        session.post(url, auth=(JENKINS_USER, JENKINS_API_TOKEN), timeout=15).raise_for_status()
        logger.info(f"{action} triggered")
    except Exception as e:
        logger.error(f"Jenkins {action} failed: {e}")

def cooldown_active() -> bool:
    global LAST_ACTION_TIME
    current = time.time()
    if current - LAST_ACTION_TIME < COOLDOWN_SECONDS:
        return True
    LAST_ACTION_TIME = current
    return False

@app.route("/alert", methods=["POST"])
def alert():
    if cooldown_active():
        return jsonify({"status": "cooldown"}), 429
    
    metrics = get_metrics()
    decision = ask_ai(metrics)
    action, reason = decision["action"], decision["reason"]

    if action == "ROLLBACK":
        trigger_jenkins_job(JENKINS_ROLLBACK_URL, "ROLLBACK")
        send_notification("ROLLBACK EXECUTED", reason)
    elif action == "SCALE":
        trigger_jenkins_job(JENKINS_SCALE_URL, "SCALE")
        send_notification("SCALE EXECUTED", reason)

    return jsonify({"metrics": metrics, "decision": action, "reason": reason})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


def monitor_loop():
    """Background thread to poll metrics and take action automatically."""
    logger.info("SRE Agent Monitoring Loop started...")
    while True:
        try:
            metrics = get_metrics()
            # We check metrics manually here without waiting for an external /alert
            decision = ask_ai(metrics)
            action, reason = decision["action"], decision["reason"]

            if action in ["ROLLBACK", "SCALE"]:
                if not cooldown_active():
                    url = JENKINS_ROLLBACK_URL if action == "ROLLBACK" else JENKINS_SCALE_URL
                    trigger_jenkins_job(url, action)
                    send_notification(f"{action} EXECUTED", reason)
                else:
                    logger.info(f"Decision was {action}, but Agent is in cooldown.")
            
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
        
        time.sleep(60) # Check every 1 minute

# Start the background thread
threading.Thread(target=monitor_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)