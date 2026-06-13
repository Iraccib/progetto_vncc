#!/usr/bin/env python3
from lqr_hpa import LQR
import sys

DEFAULT_DURATION = 120

if __name__ == "__main__":
    duration = int(sys.argv[sys.argv.index("--time") + 1]) if "--time" in sys.argv else DEFAULT_DURATION
    lqr = LQR(duration)
    lqr.run()