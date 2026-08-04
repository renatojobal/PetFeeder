# main.py -- pet feeder entry point (runs at boot).
# Connects WiFi, initialises the motor + status LED, and hands control to the bot.

import time
import config
import wifi
from motor import Motor
from bot import TelegramBot
from led import StatusLED, CONNECTING, ERROR


def main():
    print("pet feeder starting...")
    led = StatusLED(config.LED_PIN)
    led.set(CONNECTING)                 # fast blink while we get online

    motor = Motor(config)
    motor.stop()

    # Keep retrying WiFi forever -- the feeder is useless without it.
    while True:
        try:
            ip = wifi.connect(config)
            print("wifi connected:", ip[0])
            break
        except Exception as e:
            print("wifi failed, retrying:", e)
            led.set(ERROR)              # frantic blink on failure
            time.sleep(2)
            led.set(CONNECTING)

    bot = TelegramBot(config, motor, led=led)
    bot.poll_forever()


main()
