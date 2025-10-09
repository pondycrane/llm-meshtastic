import requests
import meshtastic
import meshtastic.serial_interface

from pubsub import pub
import time
import json
import time

_MAX_RESP_SIZE = 230

def send_message(interface, message: str) -> None:
    print("sending message")
    interface.sendText(message)
    time.sleep(1)

def onReceive(packet, interface):
    print(f"Received from {packet}")
    
    if "decoded" in packet:
        if packet["decoded"]["portnum"] != "TEXT_MESSAGE_APP":
            print("not text message, skipped")
            return

        msg = packet["decoded"]["payload"].decode(encoding='UTF-8', errors='strict')
    elif "encrypted" in packet:
        msg = "nah"
    else:
        print("skipped")
        return

    print("query msg", msg)
    payload = {"model": "llama3.2:1b", "prompt": msg, "stream": False}
    resp = requests.post("http://localhost:11434/api/generate", data=json.dumps(payload))
    data = resp.json()
    answer = data["response"].strip("<think>\n\n</think>\n\n")

    cur = 0
    prev = 0
    n = len(answer)
    chunk_size = 0
    while cur < n:
        cur_size = len(answer[cur].encode('utf-8'))
        if chunk_size + cur_size > _MAX_RESP_SIZE:
            send_message(interface, answer[prev: cur])
            prev = cur
            chunk_size = 0
            continue

        cur = cur + 1
        chunk_size += cur_size

    if chunk_size > 0:
        send_message(interface, answer[prev: cur])


def onConnection(interface, topic=pub.AUTO_TOPIC):
    print("Connected to Meshtastic device.")

# Choose your interface type
# For serial:
interface = meshtastic.serial_interface.SerialInterface()
# For TCP (replace with your device's IP/hostname):
# interface = meshtastic.tcp_interface.TCPInterface(hostname='192.168.68.74')

pub.subscribe(onReceive, "meshtastic.receive")
pub.subscribe(onConnection, "meshtastic.connection.established")

print("Listening for Meshtastic messages...")

try:
    while True:
        time.sleep(1000) # Keep the script running indefinitely
except KeyboardInterrupt:
    print("Exiting...")
finally:
    interface.close()


