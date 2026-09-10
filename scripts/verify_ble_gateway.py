"""
Comprehensive Automated Verification Suite for Universal BLE Sensor Gateway.
Tests:
1. Hub instantiation & multi-node initialization
2. Standard GATT characteristic decoding (Temp, Hum, Pressure, Battery, Lux)
3. Custom Protocol JSON metadata parsing & auto-channel creation
4. Derived metrics calculation (VPD, Dew Point, Heat Index, Accel Mag)
5. FastRingBuffer bounded O(1) performance & stats
6. Threshold Engine with Hysteresis anti-false-alarm
7. Alarm State Machine (NORMAL -> WARNING -> CRITICAL -> ACKNOWLEDGED -> CLEARED)
8. Session Disk Recorder (stream to CSV)
9. Unknown Sensor Mode & persistent decoder registration
10. Full 5-Tab TFT UI rendering & touch navigation
"""

import os
import sys
import time
import struct
import pygame

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy video driver for headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from core.ble_gateway import (
    UniversalBLEGateway, get_ble_gateway,
    SensorChannel, ChannelType, GraphType, SensorSample,
    AlertLevel, AlarmEvent, ThresholdConfig,
    FastRingBuffer, UniversalDataDecoder, DecoderRegistry,
    DerivedMetricsEngine, ThresholdEngine, SessionRecorder
)
from ui.views.ble_gates_view import BLEGatesView
from ui.theme import ThemeManager


def run_tests():
    print("=" * 65)
    print("  [*] Universal BLE Sensor Gateway Verification Suite")
    print("=" * 65)

    passed = 0
    total = 0

    def check(name: str, condition: bool, details: str = ""):
        nonlocal passed, total
        total += 1
        status = "[OK]  " if condition else "[FAIL]"
        if condition:
            passed += 1
        print(f"  {status} {name}" + (f" ({details})" if details else ""))
        if not condition:
            print(f"         FAILED DETAILS: {details}")

    # --- TEST 1: Hub & Multi-Node Discovery ---
    gateway = get_ble_gateway()
    check("Gateway Hub Instantiated", gateway is not None)
    nodes = list(gateway.nodes.keys())
    check("Multi-Node Discovery", len(nodes) >= 3, f"found {len(nodes)} nodes: {nodes}")

    nrf = gateway.nodes.get("node_nrf_01") or gateway.nodes.get("node_nrf52832")
    check("nRF52832 BME680 Node Present", nrf is not None and "temp" in nrf.channels)

    # --- TEST 2: Standard GATT Characteristic Decoding ---
    decoder = gateway.decoder
    # Temp 25.40 C (0x2A6E: 2540 = 0x0EEC)
    temp_bytes = struct.pack("<h", 2540)
    res = decoder.decode_gatt_standard("00002a6e-0000-1000-8000-00805f9b34fb", temp_bytes)
    check("GATT Temp 0x2A6E Decoded", res == ("temp", 25.4, "°C"), f"got {res}")

    # Hum 58.5 % (0x2A6F: 5850 = 0x16DA)
    hum_bytes = struct.pack("<H", 5850)
    res = decoder.decode_gatt_standard("00002a6f-0000-1000-8000-00805f9b34fb", hum_bytes)
    check("GATT Hum 0x2A6F Decoded", res == ("hum", 58.5, "%"), f"got {res}")

    # Pressure 1013.25 hPa (0x2A6D: 1013250 = 0x000F75E2)
    pres_bytes = struct.pack("<I", 1013250)
    res = decoder.decode_gatt_standard("00002a6d-0000-1000-8000-00805f9b34fb", pres_bytes)
    check("GATT Pressure 0x2A6D Decoded", res == ("pressure", 1013.25, "hPa"), f"got {res}")

    # Battery 88% (0x2A19)
    batt_bytes = bytes([88])
    res = decoder.decode_gatt_standard("00002a19-0000-1000-8000-00805f9b34fb", batt_bytes)
    check("GATT Battery 0x2A19 Decoded", res == ("battery", 88.0, "%"), f"got {res}")

    # --- TEST 3: Custom Protocol Metadata Auto-Creation ---
    meta_json = {
        "device": "CUSTOM_ESP32",
        "channels": [
            {"id": "soil_moisture", "name": "Soil Moisture", "type": "moisture", "unit": "%"},
            {"id": "co2_level", "name": "CO2 Concentration", "type": "gas", "unit": "ppm"}
        ]
    }
    channels = decoder.parse_metadata_advertisement(meta_json)
    check("Custom Protocol Metadata Parser", len(channels) == 2 and channels[0].id == "soil_moisture" and channels[1].channel_type == ChannelType.GAS)

    # --- TEST 4: Derived Metrics Engine (VPD, Dew Point, Heat Index, Accel Mag) ---
    vpd = DerivedMetricsEngine.compute_vpd(27.4, 68.2)
    check("VPD Calculation (27.4C, 68.2%)", 1.0 <= vpd <= 1.5, f"VPD = {vpd} kPa")

    dew_pt = DerivedMetricsEngine.compute_dew_point(27.4, 68.2)
    check("Dew Point Calculation (27.4C, 68.2%)", 20.0 <= dew_pt <= 22.0, f"Dew Point = {dew_pt} °C")

    heat_idx = DerivedMetricsEngine.compute_heat_index(30.0, 75.0)
    check("Heat Index Calculation (30.0C, 75.0%)", 34.0 <= heat_idx <= 38.0, f"Heat Index = {heat_idx} °C")

    accel_mag = DerivedMetricsEngine.compute_accel_magnitude(0.0, 0.0, 1.0)
    check("3D Accel Magnitude (0, 0, 1g)", abs(accel_mag - 1.0) < 0.001, f"Mag = {accel_mag} g")

    # --- TEST 5: FastRingBuffer Performance & Memory Bounds ---
    buf = FastRingBuffer(maxlen=60)
    t0 = time.time()
    for k in range(500):
        buf.append(t0 + k * 0.1, 20.0 + (k % 10))
    check("Ring Buffer Length Bounded to 60", len(buf.buffer) == 60)
    cur, min_v, max_v, avg_v = buf.get_stats()
    check("Ring Buffer Stats", min_v == 20.0 and max_v == 29.0, f"min={min_v}, max={max_v}")

    # --- TEST 6: Threshold Engine & Hysteresis ---
    th_engine = ThresholdEngine()
    test_ch = SensorChannel(id="test_temp", name="Test Temp", channel_type=ChannelType.TEMP, unit="°C", current_val=25.0)
    cfg = ThresholdConfig(channel_id="test_temp", enabled=True, warn_high=80.0, crit_high=100.0, hysteresis_pct=3.0)
    th_engine.set_config(cfg)

    # Below threshold -> NORMAL
    lvl = th_engine.evaluate_channel(test_ch, "dev1")
    check("Threshold Nominal Level", lvl == AlertLevel.NORMAL)

    # Exceeds Warn -> WARNING
    test_ch.current_val = 82.0
    lvl = th_engine.evaluate_channel(test_ch, "dev1")
    check("Threshold Warning Level", lvl == AlertLevel.WARNING)

    # Exceeds Crit -> CRITICAL
    test_ch.current_val = 101.5
    lvl = th_engine.evaluate_channel(test_ch, "dev1")
    check("Threshold Critical Level", lvl == AlertLevel.CRITICAL)

    # Hysteresis Check: Value drops to 99.0 C (between 100 and 97 clear threshold) -> MUST REMAIN CRITICAL!
    test_ch.current_val = 99.0
    lvl = th_engine.evaluate_channel(test_ch, "dev1")
    check("Hysteresis Anti-False-Alarm (99.0C >= 97.0C Clear)", lvl == AlertLevel.CRITICAL, f"level={lvl}")

    # Value drops to 96.0 C (< 97.0 C Clear) -> Transitions to WARNING (since 96 >= 80)
    test_ch.current_val = 96.0
    lvl = th_engine.evaluate_channel(test_ch, "dev1")
    check("Hysteresis Cleared Critical to Warning", lvl == AlertLevel.WARNING, f"level={lvl}")

    # --- TEST 7: Alarm State Machine & Acknowledge ---
    test_ch.current_val = 103.0
    th_engine.evaluate_channel(test_ch, "dev1")
    check("Active Critical Alarm Present", th_engine.has_critical_alarm())

    # User acknowledges
    th_engine.acknowledge_alarm("test_temp")
    check("Alarm Acknowledged State", not th_engine.has_critical_alarm() and th_engine.active_alarms["test_temp"].state == "ACKNOWLEDGED")

    # --- TEST 8: Session Disk Recorder ---
    recorder = SessionRecorder()
    filepath = recorder.start_session()
    check("Session File Created", os.path.exists(filepath))
    sample = SensorSample(timestamp=time.time(), device_id="test_node", channel_id="temp", value=26.5, unit="°C")
    recorder.record_sample(sample)
    recorder.stop_session()
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    check("Session Data Streamed to Disk", "temp,26.5,°C" in content)
    recorder.clear_current_session()
    check("Session Cleaned", not os.path.exists(filepath))

    # --- TEST 9: Unknown Sensor Decoder Persistence ---
    reg = DecoderRegistry()
    reg.save_decoder("unknown_char_1234", {"format": "<f", "scale": 1.0, "offset": 0.0, "name": "Custom Float"})
    check("Unknown Sensor Decoder Persisted", "unknown_char_1234" in reg.user_decoders)

    # --- TEST 10: Full 5-Tab TFT UI Rendering & Touch ---
    screen = pygame.Surface((240, 320))
    tm = ThemeManager()
    fonts = {
        "header": pygame.font.Font(None, 14),
        "body": pygame.font.Font(None, 12),
        "small": pygame.font.Font(None, 10),
        "title": pygame.font.Font(None, 16)
    }

    # Render LIVE tab
    BLEGatesView.active_tab = "LIVE"
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: LIVE Tab", True)

    # Render GRAPH tab
    BLEGatesView.active_tab = "GRAPH"
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: GRAPH Tab", True)

    # Render RAW tab
    BLEGatesView.active_tab = "RAW"
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: RAW Tab", True)

    # Render DEV tab
    BLEGatesView.active_tab = "DEV"
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: DEV Tab", True)

    # Render ALERTS tab
    BLEGatesView.active_tab = "ALERTS"
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: ALERTS Tab", True)

    # Render Threshold Modal
    BLEGatesView.modal_open = True
    BLEGatesView.render(screen, fonts, tm.colors, 0)
    check("UI Render: Threshold Config Modal", True)
    BLEGatesView.modal_open = False

    # Test Touch Handler Navigation
    view_inst = BLEGatesView()
    act = view_inst.handle_touch((20, 30))  # Back to Home
    check("Touch Back Home Action", act == "BACK_HOME")

    print("=" * 65)
    print(f"  >> RESULT: {passed}/{total} Gateway Tests Passed Successfully!")
    print("=" * 65)

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
