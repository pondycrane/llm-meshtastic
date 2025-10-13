import requests
import meshtastic
import meshtastic.serial_interface

from pubsub import pub
import time
import json
import time
from typing import Union

from meshtastic import (
    BROADCAST_ADDR,
)

_MAX_RESP_SIZE = 230

def send_message(interface, message: str, destinationId: Union[int, str, None]) -> None:
    print(f"To {destinationId}: {message}")
    # FIXME: Sending to dm by setting destinationId only sends the last message.
    interface.sendText(message, destinationId=destinationId, wantAck=True)

def onReceive(packet, interface):
    if packet["decoded"]["portnum"] != "TEXT_MESSAGE_APP":
        return

    is_public_channel = "decoded" in packet

    sender = packet.get("from")
    msg = None
    try:
        d = packet.get("decoded")

        # Reply to every received message with some stats
        msg = d.get("text")
    except Exception as ex:
        print(f"Warning: Error processing received packet: {ex}.")

    public_key = packet.get("publicKey")
    is_public_channel = public_key is None

    # Only respond to klm keyword if in public channel
    if is_public_channel and "klm" not in msg:
        return

    if is_public_channel:
        msg = msg.replace("klm", "")

    reply_to = sender
    if is_public_channel:
        reply_to = BROADCAST_ADDR

    payload = {"model": "llama3.2:1b", "prompt": msg, "stream": True}
    resp = requests.post("http://localhost:11434/api/generate", data=json.dumps(payload))

    words_buffer = []
    chunk_size = 0
    for line in resp.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            try:
                json_data = json.loads(decoded_line)
                if 'response' in json_data:

                    if chunk_size + len(json_data['response']) > _MAX_RESP_SIZE:
                        send_message(interface, "".join(words_buffer), reply_to)
                        words_buffer = []
                        chunk_size = 0

                    words_buffer.append(json_data['response'])
                    chunk_size += len(json_data['response'])
            except json.JSONDecodeError:
                # Handle cases where a line might not be a complete JSON object
                pass

    if chunk_size > 0:
        send_message(interface, "".join(words_buffer), reply_to)

    return


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


