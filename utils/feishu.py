import os
import requests


def push_feishu(text):
    webhook = os.environ["FEISHU_WEBHOOK"]

    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

    response = requests.post(webhook, json=payload, timeout=30)
    response.raise_for_status()
    print(response.text)
