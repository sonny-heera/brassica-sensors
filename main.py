from machine import I2C, ADC, Pin, unique_id
from network import WLAN, STA_IF
from time import sleep, localtime
import bme280
import ntptime
import json
import binascii
from umqtt.simple import MQTTClient # type: ignore


LOGGING: bool = False

FREQUENCY_MINUTES: int = 5

TOPIC: str = ''

WIFI_NETWORK: str = ''
WIFI_PASSWORD: str = ''

MQTT_URL: str = ''
MQTT_USER: str = ''
MQTT_PASSWORD: str = ''

bme: bme280.BME280 = None # type: ignore
moisture_sensor: ADC = None # type: ignore
light_sensor: ADC = None # type: ignore


def setup() -> None:
    data: dict = {}
    with open('config.json', 'r') as file:
        data = json.load(file)

    global LOGGING, FREQUENCY_MINUTES, TOPIC, WIFI_NETWORK, WIFI_PASSWORD, MQTT_URL, MQTT_USER, \
        MQTT_PASSWORD, bme, moisture_sensor, light_sensor

    LOGGING = data['logging']
    FREQUENCY_MINUTES = data['poll-frequency-minutes']
    TOPIC = data['mqtt']['topic']
    WIFI_NETWORK = data['wifi']['ssid']
    WIFI_PASSWORD  = data['wifi']['password']

    MQTT_URL = data['mqtt']['url']
    MQTT_USER = data['mqtt']['user']
    MQTT_PASSWORD = data['mqtt']['password']

    i2c: I2C = I2C(data['temperature-sensor']['i2c-id'],
        sda=Pin(data['i2c']['sda-pin']), scl=Pin(data['i2c']['scl-pin']))
    bme = bme280.BME280(i2c=i2c)
    moisture_sensor = ADC(data['moisture-sensor']['pin'])
    light_sensor = ADC(data['light-sensor']['pin'])


def wifi_connect():
    wlan = WLAN(STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_NETWORK, WIFI_PASSWORD)

    count: int = 0
    while not wlan.isconnected() and count < 10:
        if LOGGING:
            print(f'{str(localtime())} Not connected yet')
            print(f'Networks: {wlan.scan()}')
            print(f'Status: {wlan.status()}')
            print(f'Config: {wlan.ifconfig()}')
        sleep(10)
        count += 1

    if count == 10:
        raise RuntimeError("Couldn't connect")

    if LOGGING:
        print(f'Config: {wlan.ifconfig()}')


def main() -> int:
    setup()
    sensor_id: str = binascii.hexlify(unique_id()).decode()

    while True:
        try:
            wifi_connect()
            try:
                ntptime.settime()
            except Exception as e:
                if LOGGING:
                    print(e)
            current_metrics = dict()
            current_metrics['moisture'] = moisture_sensor.read_u16()
            current_metrics['light'] = light_sensor.read_u16()
            bme_values = bme.values
            current_metrics['temperature'] = float(bme_values[0][:-1])
            current_metrics['pressure'] = float(bme_values[1][:-3])
            current_metrics['humidity'] = float(bme_values[2][:-1])

            current_time = localtime()
            current_metrics['timestamp'] = \
                f'{current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d}T' \
                f'{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}'

            client = MQTTClient(sensor_id, MQTT_URL, 1883, MQTT_USER, MQTT_PASSWORD)
            client.connect()
            msg: str = json.dumps(current_metrics)
            if LOGGING:
                print(f'{localtime()}: Message: {msg}')
            client.publish(TOPIC, json.dumps(current_metrics), qos=1, retain=True)
            client.disconnect()
            wlan = WLAN(STA_IF)
            wlan.disconnect()
            wlan.active(False)
            wlan.deinit()
            sleep(60 * FREQUENCY_MINUTES)
        except Exception as e:
            if LOGGING:
                print(f'{localtime()}: {e}')
            wlan = WLAN(STA_IF)
            wlan.disconnect()
            wlan.active(False)
            wlan.deinit()
            sleep(30)


main()