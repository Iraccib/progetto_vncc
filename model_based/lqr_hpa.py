import numpy as np
import control as cntrl
from kubernetes import client, config
import time, csv, datetime, threading

from latency import LatencyManage

class LQR:
    def __init__(self, duration_s: float = 300.0):
        # =========================== PARAMETRI ==================================
        self.BETA         = 0.2    
        self.Tc           = 1.0    

        self.Q_WEIGHT     = 5.0    
        self.R_WEIGHT     = 10.0    

        self.MIN_REPLICAS = 1
        self.MAX_REPLICAS = 10

        self.duration_s   = duration_s

        self.LAT_REF = 0.4

        self.MAX_DELTA = 4
        self.bound = 0

        self.COOLDOWN_STEPS = 5
        self.scale_down_allowed_at_step = 0

        # =========================== MODELLO DINAMICO ===========================
        self.A_ = np.array([[1 - self.BETA]])
        self.B_ = np.array([[self.BETA]])
        self.Q_ = np.array([[self.Q_WEIGHT]])
        self.R_ = np.array([[self.R_WEIGHT]])
        self.K_x = 0.0

        self.u_not_sat = 0

        self.log = []

        self.latency = LatencyManage()
        self.latency._scale_deployment(self.MIN_REPLICAS)

    def design_controller(self):
        [K, _, _] = cntrl.dlqr(self.A_, self.B_, self.Q_, self.R_)
        self.K_x = float(K[0, 0])
        pole_x   = float(self.A_[0, 0] - self.B_[0, 0] * self.K_x)
        self.bound = int(self.MAX_DELTA / (1 + self.K_x))
        print(f"[GAIN] K_x={self.K_x:.4f}")
        print(f"[POLE] Polo plant ciclo chiuso: z={pole_x:.4f}")
        print(f"[BOUND] MAX ALLOW SCALE: {self.bound}")
        assert abs(pole_x) < 1.0, f"Polo plant instabile: {pole_x}"

    def step(self, x_k: int, l_k: float, k: int):
        
        x_ref = float(x_k) * (l_k / self.LAT_REF)
        x_ref = float(np.clip(x_ref, self.MIN_REPLICAS, self.MAX_REPLICAS))

        x_tilde = x_k - x_ref
        u_k     = x_ref - self.K_x * x_tilde

        self.u_not_sat = int(u_k)

        u_sat = int(np.clip(round(u_k), self.MIN_REPLICAS, self.MAX_REPLICAS))

        if u_sat > x_k:
            self.scale_down_allowed_at_step = k + self.COOLDOWN_STEPS
        elif u_sat < x_k:
            if k < self.scale_down_allowed_at_step:
                u_sat = x_k

        delta = u_sat - x_k
        if abs(delta) > self.bound:
            u_sat = x_k + int(np.sign(delta) * self.bound)

        e_k     = l_k - self.LAT_REF
        z = max(0.0, e_k) * x_k

        return u_sat, x_ref, x_tilde, e_k, z

    def run(self):
        self.print_log()
        self.design_controller()

        t_start = time.time()
        k = 0
        try:
            while (time.time() - t_start) < self.duration_s:
                t_loop = time.time()
                t_now  = t_loop - t_start

                l_k, y_k = self.latency.get_latency()
                if l_k is None:
                    print(f"[k={k}] Sensore non disponibile, skip step")
                    k += 1
                    time.sleep(self.Tc)
                    continue

                x_k = self.latency.get_pod_count()
                u, x_ref, x_tilde, e_k, z = self.step(x_k, l_k, k)
                self.latency._scale_deployment(u)

                self.log_step(k, t_now, l_k, y_k, e_k, x_ref, x_k, u, z)
                k += 1

                elapsed = time.time() - t_loop
                time.sleep(max(0.01, self.Tc - elapsed))

        except KeyboardInterrupt:
            print("\n[INFO] Interrotto dall'utente")

        self.save_log()

    def log_step(self, k, t, l_k, y_k, e_k, x_ref, x, u, z):
        entry = dict(
            k=k, t=round(t, 2), l=round(l_k, 4), y=y_k,
            e=round(e_k, 4), x_ref=round(x_ref, 2),
            x=x, u=u, z=round(z, 2), suffering=round(z, 2)
        )

        self.log.append(entry)
        tag = "▲" if u > x else ("▼" if u < x else "─")
        print(
            f"[k={k:3d} t={t:5.1f}s] l={l_k:.3f}s y={y_k} e={e_k:+.3f} "
            f"x_ref={x_ref:5.1f}  x={x:3d}  u={u:3d}{tag}  z={z:+6.1f} u={self.u_not_sat:3d}{tag}")

    def save_log(self) -> str:
        if not self.log:
            print("[WARN] Log vuoto.")
            return ""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"../data/lqr_log_{ts}.csv"
        with open(fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.log[0].keys())
            w.writeheader()
            w.writerows(self.log)
        print(f"\n[LOG] Salvato in {fn}")
        return fn

    def print_log(self):
        print("=" * 64)
        print("  LQR AUTOSCALER ")
        print(f"  Duration: {self.duration_s}s  Tc={self.Tc}s")
        print(f"  BETA={self.BETA}          TARGET_LATENZA={self.LAT_REF}")
        print(f"  Q={self.Q_WEIGHT}         R={self.R_WEIGHT}")
        print(f"  min={self.MIN_REPLICAS}   max={self.MAX_REPLICAS}")
        print("=" * 64 + "\n")