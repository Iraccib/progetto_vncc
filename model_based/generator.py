import requests
import concurrent.futures
import csv
import datetime
import time
import threading

URL     = "http://calculator-lqr-service:5000/calculate"
PAYLOAD = {"value": 20}

TOTAL_REQUESTS     = 10000
CONCURRENT_WORKERS = 500

log      = []
log_lock = threading.Lock()
t_start  = time.time()


def send_request(i):
    try:
        t_req    = time.time()
        response = requests.post(URL, json=PAYLOAD, timeout=5)
        latency  = round(time.time() - t_req, 4)
        print(
            f"[{i}] Status: {response.status_code} | Response: {response.json()}"
        )
        with log_lock:
            log.append(dict(
                i=i,
                t=round(t_req - t_start, 3),
                l=latency,
                status=response.status_code,
            ))
    except Exception as e:
        pass


with concurrent.futures.ThreadPoolExecutor(
    max_workers=CONCURRENT_WORKERS
    ) as executor:
        executor.map(send_request, range(TOTAL_REQUESTS))


if log:
    log.sort(key=lambda r: r["i"])
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"../data/load_log_{ts}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=log[0].keys())
        w.writeheader()
        w.writerows(log)
    print(f"\n[LOG] Salvato in {fn}")