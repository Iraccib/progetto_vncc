from flask import Flask, jsonify, request
import threading
import time

app = Flask(__name__)

MAX_CONCURRENT = 3
_semaphore = threading.Semaphore(MAX_CONCURRENT)
WORK_TIME  = 0.1  # 100ms — capacità per replica = 30 req/s

_lock    = threading.Lock()
_waiting = 0  # richieste in attesa del semaforo

# === SERVICE
@app.route("/calculate", methods=["POST"])
def calculate():
    global _waiting

    data  = request.get_json(silent=True) or {}
    value = data.get("value", 0)

    with _lock:
        _waiting += 1

    acquired = _semaphore.acquire(timeout=5.0)

    with _lock:
        _waiting -= 1

    if not acquired:
        return jsonify({"error": "overloaded"}), 503

    try:
        time.sleep(WORK_TIME)
        result = value * 2
        return jsonify({"result": result, "status": "success"}), 200
    finally:
        _semaphore.release()

# === Function to compute latency
@app.route("/health", methods=["GET"])
def health():
    with _lock:
        waiting = _waiting

    # Latenza stimata: coda * WORK_TIME + servizio
    # Se waiting=0 → latency=WORK_TIME (sistema scarico)
    # Se waiting=N → latency≈(N+1)*WORK_TIME (sistema sotto carico)
    estimated_latency = (waiting + 1) * WORK_TIME

    return jsonify({
        "waiting":           waiting,
        "estimated_latency": round(estimated_latency, 4),
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
