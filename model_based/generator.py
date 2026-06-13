import requests
import concurrent.futures
import csv
import datetime
import time
import threading

URL     = "http://calculator-lqr-service:5000/calculate"
PAYLOAD = {"value": 20}

# ===============================================================
# PROFILI DI CARICO
# ===============================================================
# Ogni profilo è una lista di (duration_s, req_per_sec)
PROFILES = {
    "1": {
        "name": "Gradino singolo",
        "steps": [
            (10,  10),
            (80, 600),
            (30,  10),
        ],
    },
    "2": {
        "name": "Gradini multipli",
        "steps": [
            (10,  10),
            (40,  600),
            (10,  300),
            (40,  600),
            (20,  10),
        ],
    },
    "3": {
        "name": "Burst",
        "steps": [
            (20,  10),
            (10,  600),
            (20,  10),
            (20,  600),
            (20,  10),
            (10,  600),
            (20,  10),
        ],
    },
}

log      = []
log_lock = threading.Lock()
t_start  = 0.0


def send_request(i):
    try:
        t_req    = time.time()
        response = requests.post(URL, json=PAYLOAD, timeout=5)
        latency  = round(time.time() - t_req, 4)
        #print(
        #    f"[{i}] Status: {response.status_code} | Response: {response.json()}"
        #)
        with log_lock:
            log.append(dict(
                i=i,
                t=round(t_req - t_start, 3),
                l=latency,
                status=response.status_code,
            ))
    except Exception as e:
        pass


def run_profile(steps: list):
    global t_start
    t_start  = time.time()
    req_idx  = 0
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=500)
    futures  = []

    for duration_s, req_per_sec in steps:
        print(f"[PROFILO] {req_per_sec} req/s per {duration_s}s")
        interval  = 1.0 / req_per_sec
        t_end     = time.time() + duration_s
        while time.time() < t_end:
            t0 = time.time()
            futures.append(executor.submit(send_request, req_idx))
            req_idx += 1
            elapsed = time.time() - t0
            wait    = interval - elapsed
            if wait > 0:
                time.sleep(wait)

    executor.shutdown(wait=True)


def save_log():
    if not log:
        return
    log.sort(key=lambda r: r["i"])
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"../data/load_log_{ts}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=log[0].keys())
        w.writeheader()
        w.writerows(log)
    print(f"\n[LOG] Salvato in {fn}")


# ===============================================================
# MENU
# ===============================================================
print("Seleziona profilo di carico:")
for k, v in PROFILES.items():
    total = sum(d for d, _ in v["steps"])
    print(f"  {k}) {v['name']}  (durata totale: {total}s)")

choice = input("\nScelta [1/2/3]: ").strip()
if choice not in PROFILES:
    print("[ERRORE] Scelta non valida.")
    exit(1)

profile = PROFILES[choice]
print(f"\n[INFO] Avvio profilo: {profile['name']}")
print(f"[INFO] Target: {URL}\n")

run_profile(profile["steps"])
save_log()