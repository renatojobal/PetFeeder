# wifi.py -- connect the ESP32 to WiFi in station mode
import time
import network


def connect(cfg, timeout_ms=30000, rekick_ms=6000):
    """Connect to the configured WiFi. Returns ifconfig() tuple on success.

    Re-issues the connect request every ``rekick_ms`` because after a reset the
    AP may still hold the old (undeauthed) association and stall the first try.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan.ifconfig()
    start = time.ticks_ms()
    last_kick = None
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if wlan.isconnected():
            return wlan.ifconfig()
        now = time.ticks_ms()
        if last_kick is None or time.ticks_diff(now, last_kick) > rekick_ms:
            try:
                wlan.disconnect()
            except OSError:
                pass
            time.sleep_ms(150)
            wlan.connect(cfg.WIFI_SSID, cfg.WIFI_PASSWORD)
            last_kick = now
        time.sleep_ms(250)
    raise RuntimeError("wifi connect timeout for SSID %r (status=%d)"
                       % (cfg.WIFI_SSID, wlan.status()))


def is_connected():
    return network.WLAN(network.STA_IF).isconnected()
