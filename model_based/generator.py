import requests
import concurrent.futures

URL  = "http://calculator-lqr-service:5000/calculate"
PAYLOAD = {"value": 20}

TOTAL_REQUESTS = 10000
CONCURRENT_WORKERS = 300

def send_request(i):
    try:
        response = requests.post(URL, json=PAYLOAD, timeout=5)
        print(
            f"[{i}] Status: {response.status_code} | Response: {response.json()}"
        )
    except Exception as e:
        pass

with concurrent.futures.ThreadPoolExecutor(
    max_workers=CONCURRENT_WORKERS
    ) as executor:
        executor.map(send_request, range(TOTAL_REQUESTS))