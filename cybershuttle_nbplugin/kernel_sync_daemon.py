"""
Periodically sync available kernels with Cybershuttle Gateway

@author: Yasith Jayawardana <yasith@cs.odu.edu>

"""

import requests
import schedule
import json
import time
import argparse


def sync_cybershuttle_kernels_with_localfs():
    try:
        response = requests.get(url)  # Replace with your URL
        if response.status_code == 200:
            data = response.json()
            with open("data.json", "w") as f:
                json.dump(data, f)
            print("Data updated successfully.")
        else:
            print("Failed to fetch data. Status code:", response.status_code)
    except Exception as e:
        print("An error occurred:", e)


if __name__ == "__main__":
    # Schedule the job to run every hour
    N = 5
    parser = argparse.ArgumentParser(description="Periodically sync available kernels with Cybershuttle Gateway")
    parser.add_argument("url", type=str, help="URL of Cybershuttle Gateway Server")
    args = parser.parse_args()
    url = args.url

    schedule.every(N).seconds.do(sync_cybershuttle_kernels_with_localfs)

    while True:
        schedule.run_pending()
        time.sleep(N / 2)
