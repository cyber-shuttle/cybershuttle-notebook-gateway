"""
Periodically sync available kernels with Cybershuttle Gateway

@author: Yasith Jayawardana <yasith@cs.odu.edu>

"""

import argparse
import json
import os
import time
from pathlib import Path

import requests
import schedule


def sync_cybershuttle_kernels_with_localfs():
    try:
        response = requests.get(f"{url}/kernelspecs")
        if response.status_code == 200:
            data: dict[str, dict] = response.json()
            for kernel_name, kernel_spec in data.items():
                kernel_fp = kernel_dir / kernel_name
                kernel_spec["display_name"] = kernel_name
                os.makedirs(kernel_fp, exist_ok=True)
                with open(kernel_fp / "kernel.json", "w") as f:
                    json.dump(kernel_spec, f)
            print(f"Wrote {len(data)} kernels to {kernel_dir}")
        else:
            print(f"Got HTTP {response.status_code} error for kernel request")
    except Exception as e:
        print("Error getting kernels:", e)


if __name__ == "__main__":
    # Schedule the job to run every hour
    N = 5
    parser = argparse.ArgumentParser(description="Periodically sync available kernels with Cybershuttle Gateway")
    parser.add_argument("--url", "-u", type=str, help="URL of Cybershuttle Gateway Server")
    parser.add_argument("--kernel_dir", "-k,", type=str, help="Path to store kernel specs")
    args = parser.parse_args()
    url = args.url
    kernel_dir = os.path.expandvars(args.kernel_dir)
    kernel_dir = Path(kernel_dir).expanduser().absolute()

    schedule.every(N).seconds.do(sync_cybershuttle_kernels_with_localfs)

    while True:
        schedule.run_pending()
        time.sleep(N / 2)
