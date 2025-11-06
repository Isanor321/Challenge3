# main.py - ESP32 MQTT Controlled LED
#
# This script is a streamlined IoT controller that connects to Wi-Fi,
# connects to an MQTT broker, and controls an LED based on messages
# received on a subscribed topic. It reports the LED status back.

import time
import machine
import network
from umqtt.robust import MQTTClient
import ubinascii

# --- 1. CONFIGURATION ---

# Load Wi-Fi credentials from wifi_connect.py
try:
    from wifi_connect import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    print("FATAL: wifi_connect.py missing. Cannot connect to Wi-Fi.")
    WIFI_SSID = "Tabula_Rasa"
    WIFI_PASSWORD = "fhqyrvncaz"
    
# REPLACE 'youlikejazz?' with your actual unique name/identifier string.
MY_UNIQUE_IDENTIFIER = "youlikejazz?"

# Hardware Setup (Using Pin 23 for external LED on breadboard)
LED_PIN = 2
LED = machine.Pin(LED_PIN, machine.Pin.OUT)

# MQTT Broker Details
MQTT_BROKER = "broker.hivemq.com"
PORT = 1883

# Build Topics and Client ID using the unique identifier
TOPIC_BASE = f"wyohack/{MY_UNIQUE_IDENTIFIER}/led"
TOPIC_COMMAND = TOPIC_BASE.encode() + b"/command"
TOPIC_STATUS = TOPIC_BASE.encode() + b"/status"

# Ensure Client ID is unique
MAC_HEX = ubinascii.hexlify(machine.unique_id()).decode()
CLIENT_ID = f"esp32_led_controller_{MY_UNIQUE_IDENTIFIER}_{MAC_HEX}".encode()

# Global MQTT Client variable
client = None


# --- 2. NETWORK & MQTT FUNCTIONS ---

def connect_wifi():
    """Connect to the Wi-Fi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True

    print(f"Connecting to Wi-Fi: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Wait for connection (max 10 seconds)
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        print('.', end='')
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        print('\nWi-Fi connected. Config:', wlan.ifconfig())
        return True
    
    print("\nWi-Fi connection failed!")
    return False

def sub_cb(topic, msg):
    """Callback function for incoming MQTT messages."""
    
    # DEBUG: See the raw bytes received
    print(f"DEBUG: Raw Msg Bytes: {msg}") 
    
    # FINAL ROBUSTNESS FIX: 
    # 1. Decode to string.
    # 2. Strip *all* potential surrounding characters: whitespace, newlines, AND quotes.
    # 3. Remove internal null bytes.
    # 4. Convert to uppercase.
    command = msg.decode().strip(' \n\r\t"\'').replace('\x00', '').upper() 
    
    # DEBUG: Check the length of the cleaned string
    print(f"DEBUG: Cleaned Command Length: {len(command)}")
    print(f"Received Command: {command}")
    
    status_to_publish = None

    # The command should now be a clean "ON" or "OFF"
    if command.startswith("ON"):
        LED.value(1)
        status_to_publish = b"ON"
    elif command.startswith("OFF"):
        LED.value(0)
        status_to_publish = b"OFF"
    else:
        print("Unknown command. Ignoring.")
        
    # Publish status confirmation
    if status_to_publish:
        client.publish(TOPIC_STATUS, status_to_publish)
        print(f"Published status: {status_to_publish.decode()}")

def connect_mqtt():
    """Connect to the MQTT broker and subscribe."""
    global client
    
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, PORT)
    client.set_callback(sub_cb)
    
    print(f"Attempting MQTT connection with Client ID: {CLIENT_ID.decode()}")
    
    try:
        client.connect()
        client.subscribe(TOPIC_COMMAND)
        print(f"MQTT Connected! Subscribed to: {TOPIC_COMMAND.decode()}")
        return True
    except Exception as e:
        print(f"Could not connect to MQTT broker: {e}")
        return False


# --- 3. MAIN EXECUTION ---

def run_device():
    """Main execution loop for the IoT device."""
    
    # 1. Ensure Connections are established
    if not connect_wifi():
        print("Failed to connect to Wi-Fi. Restarting in 5s.")
        time.sleep(5)
        machine.reset() 

    if not connect_mqtt():
        print("Failed to connect to MQTT. Restarting in 5s.")
        time.sleep(5)
        machine.reset()

    # 2. Main Loop
    print("\nDevice is running and listening...")
    
    while True:
        try:
            client.check_msg() 
            time.sleep(0.5) # Check every half-second
            
        except OSError as e:
            print(f"Connection lost ({e}). Reconnecting...")
            time.sleep(2)
            try:
                client.reconnect()
                print("Reconnection successful.")
            except Exception as re:
                print(f"Reconnection failed: {re}")
                time.sleep(5) # Wait longer if reconnect fails
        
        except KeyboardInterrupt:
            print("Application stopped.")
            break

if __name__ == "__main__":
    run_device()