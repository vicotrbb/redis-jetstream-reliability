"""Capture a new sealed collection; campaign and attempt IDs are mandatory."""
import sys
from run_homelab import main

if __name__ == "__main__":
    sys.argv[1:1] = ["collect"]
    main()
