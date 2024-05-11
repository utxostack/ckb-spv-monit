import json
import time

import requests

import json
import requests
import prometheus_client
from prometheus_client import Gauge
from prometheus_client.core import CollectorRegistry
from flask import Response, Flask
from dotenv import dotenv_values

config = dotenv_values(".env")

NodeFlask = Flask(__name__)

CKB_SPV_MONIT_URL =config['CKB_SPV_MONIT_URL']
CKB_URL = config['CKB_URL']
CONTRACT_CODE_HASH = config['CONTRACT_CODE_HASH']
ARG = config['ARG']
BTC_RPC_URL = config['BTC_RPC_URL']




def convert_int(value):
    try:
        return int(value)
    except ValueError:
        return int(value, base=16)
    except Exception as exp:
        raise exp


class BTCRPCClient:
    def __init__(self, url):
        self.url = url

    def getchaintips(self):
        return call(self.url, "getchaintips", [])

    def getblockheader(self, blockhash):
        return call(self.url, "getblockheader", [blockhash])


class MonitRPCClient:
    def __init__(self, url):
        self.url = url

    def get_ckb_client_message(self, ckb_url, code_hash, arg):
        return call(self.url, "get_ckb_client_message", [ckb_url, code_hash, arg])


def call(url, method, params, try_count=15):
    headers = {'content-type': 'application/json'}
    data = {
        "id": 42,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    print(f"request:url:{url},data:\n{json.dumps(data)}")
    for i in range(try_count):
        try:
            response = requests.post(url, data=json.dumps(data), headers=headers).json()
            print(f"response:\n{json.dumps(response)}")
            if 'error' in response.keys() and response['error'] != None:
                error_message = response['error'].get('message', 'Unknown error')
                raise Exception(f"Error: {error_message}")

            return response.get('result', None)
        except requests.exceptions.ConnectionError as e:
            print(e)
            print("request too quickly, wait 2s")
            time.sleep(2)
            continue
        except Exception as e:
            print("Exception:", e)
            raise e
    raise Exception("request time out")


@NodeFlask.route("/")
def Node_Get():
    print("-----beign---")
    CKB_SPV_Chain = CollectorRegistry(auto_describe=False)
    spv_max_height_gauge = Gauge("spv_max_height",
                                 "spv_max_height",
                                 [],
                                 registry=CKB_SPV_Chain)

    spv_current_id_gauge = Gauge("spv_current_id",
                                 "spv_current_id",
                                 [],
                                 registry=CKB_SPV_Chain)

    spv_client_size_gauge = Gauge("spv_client_size",
                                  "spv_client_size",
                                  [],
                                  registry=CKB_SPV_Chain)

    client_height_gauge = Gauge("client_height",
                                "client_height",
                                ['id'],
                                registry=CKB_SPV_Chain)
    btc_tip_height_gauge = Gauge("btc_tip_height", "btc_tip_height", registry=CKB_SPV_Chain)

    get_result = MonitRPCClient(CKB_SPV_MONIT_URL)
    clients = get_result.get_ckb_client_message(CKB_URL, CONTRACT_CODE_HASH, ARG)
    for client in clients:
        client_height_gauge.labels(id=client['id']).set(client['headers_mmr_root']['max_height'])
    client = get_max_height_client(clients)
    spv_max_height_gauge.set(client['headers_mmr_root']['max_height'])
    spv_client_size_gauge.set(len(clients))
    spv_current_id_gauge.set(client['id'])
    tipBlock = BTCRPCClient(BTC_RPC_URL).getblockheader(client['tip_block_hash'])
    tipBlock = BTCRPCClient(BTC_RPC_URL).getchaintips()
    tipHeight = tipBlock[0]['height']
    btc_tip_height_gauge.set(tipHeight)


    # BTCRPCClient(BTC_RPC_URL).get
    # btc_tip_height_gauge.set(chainTips[0]['height'])

    return Response(prometheus_client.generate_latest(CKB_SPV_Chain), mimetype="text/plain")


def get_max_height_client(clients):
    max_height_block = None
    max_height = float('-inf')  # 初始值设置为负无穷大

    for client in clients:
        if client['headers_mmr_root']['max_height'] > max_height:
            max_height = client['headers_mmr_root']['max_height']
            max_height_client = client

    return max_height_client


if __name__ == '__main__':
    NodeFlask.run(host="0.0.0.0", port=8101)
