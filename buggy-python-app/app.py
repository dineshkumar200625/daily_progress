from flask import Flask
import threading
import time

app = Flask(__name__)

memory_leak = []
bug_enabled = False

@app.route("/")
def home():
    return "Buggy Version Running"

@app.route("/enable-bug")
def enable_bug():

    global bug_enabled

    if not bug_enabled:
        bug_enabled = True

        thread = threading.Thread(target=buggy_function)
        thread.start()

    return "Bug enabled"

def buggy_function():

    global memory_leak

    while bug_enabled:

        memory_leak.append("X" * 1000000)

        x = 0
        while True:
            x += 1

        time.sleep(0.1)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)