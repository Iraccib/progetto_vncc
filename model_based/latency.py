import time
import threading
import requests
from kubernetes import client, config


class LatencyManage:
    NAMESPACE       = "default"
    DEPLOYMENT_NAME = "calculator-lqr"
    SERVICE_URL  = "http://calculator-lqr-service:5000/calculate"
    PROBE_INTERVAL  = 0.5
    PROBE_TIMEOUT   = 6.0

    def __init__(self):
        config.load_kube_config()
        self.apps_v1 = client.AppsV1Api()

        self._lock      = threading.Lock()
        self._current_l = 0.0
        self._current_y = -1

        t = threading.Thread(target=self._probe_loop, daemon=True)
        t.start()

    def _probe_loop(self):
        while True:
            t0 = time.perf_counter()
            try:
                resp = requests.post(
                    self.SERVICE_URL,
                    json={"value": 10},
                    timeout=self.PROBE_TIMEOUT
                )
                dt = time.perf_counter() - t0
                with self._lock:
                    self._current_l = dt
                    if resp.status_code == 200:
                        self._current_y = resp.json().get("result", -1)
                    else:
                        self._current_y = resp.status_code
            except Exception as e:
                print(f"[PROBE ERROR] {e}")

            time.sleep(self.PROBE_INTERVAL)

    def get_latency(self):
        with self._lock:
            return self._current_l, self._current_y

    def get_pod_count(self):
        dep = self.apps_v1.read_namespaced_deployment(
            name=self.DEPLOYMENT_NAME, namespace=self.NAMESPACE
        )
        return dep.spec.replicas if dep.spec.replicas is not None else 1

    def _scale_deployment(self, replicas: int):
        body = {"spec": {"replicas": int(replicas)}}
        self.apps_v1.patch_namespaced_deployment(
            name=self.DEPLOYMENT_NAME, namespace=self.NAMESPACE, body=body
        )