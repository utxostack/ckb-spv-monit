import time
import discord
import asyncio

import json
import requests
from dotenv import dotenv_values
import random

config = dotenv_values(".env")

CHANNEL_ID = config['CHANNEL_ID']
TOKEN = config['TOKEN']
CHECK_INTERVAL = int(config['CHECK_INTERVAL'])

MAX_CONFIRMATIONS = int(config['MAX_CONFIRMATIONS'])
CKB_SPV_MONIT_URL = config['CKB_SPV_MONIT_URL']
CKB_URL = config['CKB_URL']
CONTRACT_CODE_HASH = config['CONTRACT_CODE_HASH']
ARG = config['ARG']
BTC_RPC_URL = config['BTC_RPC_URL']
CKB_SPV_RPC_URL = config['CKB_SPV_RPC_URL']
# error
CLIENT_COUNT_CHANGE = 101
CLIENT_TIP_NUMBER_TOO_LOW = 102
CLIENT_NOT_IN_MAIN_CHAIN = 103
CLIENT_HASH_NOT_FOUND = 104
VALID_TX_VERIFY_FAILED = 105
NOT_IN_CHAIN_TX_VERIFY_SUCCESSFUL = 106
CLIENT_NOT_ORDER = 107
MONIT_SERVER_RPC_ERROR = 108
CKB_URL_ERROR = 109
BTC_PRC_ERROR = 110
CKB_SPV_SERVER_ERROR = 111

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def send_message(message):
    channel = client.get_channel(int(CHANNEL_ID))
    await channel.send(message)


# Custom function to send message
async def discord_send_message(message):
    await send_message(message)


@client.event
async def on_ready():
    print(f'已登录为 {client.user}')
    await main()
    await client.close()


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

    def getblock(self, blockhash):
        return call(self.url, "getblock", [blockhash])


class CKBSPVRPCClient:

    def __init__(self, url):
        self.url = url

    def getTxProof(self, btcId, index, confor):
        return call(self.url, "getTxProof", [btcId, index, confor])


class CKBClient:
    def __init__(self, url):
        self.url = url

    def get_transaction(self, tx):
        return call(self.url, "get_transaction", [tx])


class MonitRPCClient:
    def __init__(self, url):
        self.url = url

    def get_ckb_client_message(self, ckb_url, code_hash, arg):
        return call(self.url, "get_ckb_client_message", [ckb_url, code_hash, arg])

    def verify_tx(self, proof, btc_id, ckb_client_data):
        return call(self.url, "verify_tx", [proof, btc_id, ckb_client_data])


def call(url, method, params, try_count=30):
    headers = {'content-type': 'application/json'}
    data = {
        "id": 42,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }

    for i in range(try_count):
        try:
            response = requests.post(url, data=json.dumps(data), headers=headers, timeout=20)
            if response.status_code == 502:
                raise requests.exceptions.ConnectionError("502 ,try again")
            response = response.json()
            if 'error' in response.keys() and response['error'] != None:
                print(f"err request:url:{url},data:\n{json.dumps(data)}")
                print(f"err response:\n{json.dumps(response)}")
                error_message = response['error'].get('message', 'Unknown error')
                raise Exception(f"Error: {error_message}")
            return response.get('result', None)
        except requests.exceptions.ConnectionError as e:
            print(e)
            print(f"err request:url:{url},data:\n{json.dumps(data)}")
            print("request too quickly, wait 2s")
            time.sleep(2)
            continue
        except Exception as e:
            print("Exception:", e)
            raise e
    raise Exception("request time out")


async def discord_send_error_message(error, message):
    message = f"@here {message}"
    print(f"[discord_send_error_message]error:{error},message:{message}")
    await discord_send_message(f"[discord_send_error_message]error:{error},message:{message}")
    with open('failed.txt', 'a') as file:
        file.write(f"[discord_send_error_message]error:{error},message:{message}\n")
    await asyncio.sleep(30)


async def main():
    btcClient = BTCRPCClient(BTC_RPC_URL)
    monitClient = MonitRPCClient(CKB_SPV_MONIT_URL)
    clients = monitClient.get_ckb_client_message(CKB_URL, CONTRACT_CODE_HASH, ARG)
    ckb_spv_client = CKBSPVRPCClient(CKB_SPV_RPC_URL)
    ckb_spv_size = len(clients)
    ckbClient = CKBClient(CKB_URL)
    last_message_time = time.time()
    size = 0
    verify_successful = 0
    while True:
        size += 1
        print(f"------------current :{size}----------")
        try:
            clients = monitClient.get_ckb_client_message(CKB_URL, CONTRACT_CODE_HASH, ARG)
            if ckb_spv_size != len(clients):
                await discord_send_error_message(CLIENT_COUNT_CHANGE,
                                                 f"expected:{ckb_spv_size},but found  :{len(clients)}")
        except Exception as e:
            await discord_send_error_message(MONIT_SERVER_RPC_ERROR, f"{CKB_SPV_MONIT_URL} can't use,err:{e}")
            await asyncio.sleep(60)
            continue

        try:
            blockHeader = btcClient.getblockheader(clients[0]['tip_block_hash'])
        except Exception as e:
            if "Block not found" in e.args:
                await discord_send_error_message(CLIENT_HASH_NOT_FOUND,
                                                 f"block hash not found:{clients[0]['tip_block_hash']}")
                continue
            await discord_send_error_message(BTC_PRC_ERROR,
                                             f"BTC_RPC_URL:{BTC_RPC_URL} can‘t use,err:{e},tip_block_hash:{clients[0]['tip_block_hash']}")
            continue
        # CLIENT_NOT_IN_MAIN_CHAIN
        if blockHeader['confirmations'] == -1:
            await discord_send_error_message(CLIENT_NOT_IN_MAIN_CHAIN, f"client{clients[0]['id']}:{clients[0]['tip_block_hash']} not in main chain")
            continue

        if blockHeader['confirmations'] > MAX_CONFIRMATIONS:
            await discord_send_error_message(CLIENT_TIP_NUMBER_TOO_LOW,
                                             f"client{clients[0]['id']} tip number too low ,confirmations:{blockHeader['confirmations']}")
            continue
        rand_ckb_spv_index = random_number = random.randint(2, ckb_spv_size - 1)
        try:
            block = btcClient.getblock(clients[rand_ckb_spv_index]['tip_block_hash'])
        except Exception as e:
            await discord_send_error_message(BTC_PRC_ERROR,
                                             f"BTC_RPC_URL:{BTC_RPC_URL} can‘t use,err:{e},client[{rand_ckb_spv_index}] tip_block_hash:{clients[rand_ckb_spv_index]['tip_block_hash']}")
            continue

        old_spv_client_transaction = None
        random_verify_count = random.randint(3, 20)
        random_step = int(block['nTx']/random_verify_count)
        if random_step < 1:
            random_step = 2
        for i in range(0, block['nTx'], random_step):
            tx_id = block['tx'][i]
            try:
                tx_proof = ckb_spv_client.getTxProof(tx_id, i, 1)
                await asyncio.sleep(10)
            except Exception as e:
                await discord_send_error_message(CKB_SPV_SERVER_ERROR, f"err:{e},tx id:{tx_id},index:{i}")
                continue
            if old_spv_client_transaction is None:
                old_spv_client_transaction = ckbClient.get_transaction(tx_proof['spv_client']['tx_hash'])
            if tx_proof['spv_client']['tx_hash'] != old_spv_client_transaction['transaction']['hash']:
                old_spv_client_transaction = ckbClient.get_transaction(tx_proof['spv_client']['tx_hash'])
            spv_client_transaction = old_spv_client_transaction
            spv_client_data = spv_client_transaction['transaction']['outputs_data'][1]
            try:
                result = monitClient.verify_tx(tx_proof['proof'].replace("0x", ""), tx_id,
                                               spv_client_data.replace("0x", ""))
            except Exception as e:
                await discord_send_error_message(VALID_TX_VERIFY_FAILED, f"verify_tx failed :{e}")
                continue
            print(f"verify succ:{tx_id},range:{i}/{block['nTx']}")
            verify_successful+=1
            with open('successful.txt', 'a') as file:
                file.write(f"verify succ:{tx_id}\n")

            # add rand block rand txId
        await asyncio.sleep(60)
        elapsed_time = time.time() - last_message_time

        # If one hour has passed without any message sent, send the default message
        if elapsed_time >= CHECK_INTERVAL:
            await discord_send_message(f"current idx:{size},verify:{verify_successful} successful")
            last_message_time = time.time()


if __name__ == '__main__':
    client.run(TOKEN)