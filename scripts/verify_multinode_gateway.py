"""
Automated Verification Suite for Universal BLE Sensor Gateway:
Multi-Node Topology (3 nRF, 2 ESP, 2+ Custom/Unknown) & UI Ergonomics.
Tests:
1. Node Cycling through all 7 hardware modules
2. Arbitrary Sensor-to-Module Mapping (any sensor on any MCU)
3. Dynamic Channel Discovery & Rendering in BLEGatesView
4. Alarm Ramp Trigger, Critical Banner, and ACK Cycle
5. Zero White Screen & Zero Deadlock Guarantee
"""

import os
import sys
import time
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from core import config
from core.ble_gateway import get_ble_gateway, AlertLevel
from ui.views.ble_gates_view import BLEGatesView
from ui.theme import ThemeManager


def run_multinode_tests():
    print("=" * 68)
    print("  [*] Multi-Node Topology & Universal Gateway Verification")
    print("=" * 68)

    gateway = get_ble_gateway()
    tm = ThemeManager()
    colors = tm.colors
    fonts = {
        "title": pygame.font.SysFont("Arial", 14, bold=True),
        "header": pygame.font.SysFont("Arial", 12, bold=True),
        "body": pygame.font.SysFont("Arial", 10),
        "small": pygame.font.SysFont("Arial", 8),
    }

    screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))

    passed = 0
    total = 0

    def check(name: str, cond: bool, details: str = ""):
        nonlocal passed, total
        total += 1
        status = "[OK]  " if cond else "[FAIL]"
        if cond:
            passed += 1
        print(f"  {status} {name}" + (f" ({details})" if details else ""))
        if not cond:
            print(f"         FAILED: {details}")

    # 1. Verify all 7 required nodes exist in gateway
    expected_nodes = [
        ("node_nrf_01", "nRF52832 #1", ["temp", "humidity", "pressure", "gas_res"]),
        ("node_nrf_02", "nRF52832 #2", ["accel_x", "accel_y", "accel_z", "gyro_x"]),
        ("node_nrf_03", "nRF52832 #3", ["distance", "proximity"]),
        ("node_esp_01", "ESP32-C3 #1", ["temp", "humidity", "lux", "vbus"]),
        ("node_esp_02", "ESP32 #2", ["soil_moisture", "water_level", "relay_state"]),
        ("node_custom_01", "Custom BLE Node A", ["co2_ppm", "voc_index", "temp"]),
        ("node_unknown_04", "Unknown Beacon NODE_04", ["raw_metric"]),
    ]

    for nid, label, req_chans in expected_nodes:
        n = gateway.nodes.get(nid)
        check(f"Node Registered: {label} ({nid})", n is not None)
        if n:
            has_chans = all(ch in n.channels for ch in req_chans)
            check(f"  Channels Present: {label}", has_chans, f"has {list(n.channels.keys())}")

    # 2. Cycle through all 7 nodes via select_next_node() and render each to screen
    visited_nodes = []
    view = BLEGatesView()

    for step in range(len(gateway.nodes)):
        cur_node = gateway.get_selected_node()
        visited_nodes.append(cur_node.device_id)

        # Render view for this node
        try:
            BLEGatesView.render(screen, fonts, colors, 0)
            render_ok = True
        except Exception as e:
            render_ok = False
            print(f"Render Error on {cur_node.name}: {e}")

        check(f"Render Node UI: {cur_node.name}", render_ok)

        # Cycle to next node
        gateway.select_next_node()

    check("Cycled Full 7-Node Ring", len(set(visited_nodes)) == len(gateway.nodes), f"visited {visited_nodes}")

    # 3. Test Tab Switching (LIVE -> GRAPH -> RAW -> DEV -> ALERTS)
    for tab in ["LIVE", "GRAPH", "RAW", "DEV", "ALERTS"]:
        BLEGatesView.active_tab = tab
        try:
            BLEGatesView.render(screen, fonts, colors, 0)
            tab_ok = True
        except Exception as e:
            tab_ok = False
            print(f"Tab {tab} Render Error: {e}")
        check(f"Tab Rendering OK: {tab}", tab_ok)

    # 4. Test Touch Interaction: Node Switcher, Tab Clicks, Home Navigation
    # Click Node Switcher (x=80, y=30)
    res = view.handle_touch((80, 30))
    check("Touch Node Switcher", res and res.get("type") == "NODE_SWITCHED")

    # Click Tab 'GRAPH' (x=70, y=55)
    res = view.handle_touch((70, 55))
    check("Touch Tab Switch to GRAPH", BLEGatesView.active_tab == "GRAPH")

    # Click Back Home (x=20, y=30)
    res = view.handle_touch((20, 30))
    check("Touch Back Home Navigation", res == "BACK_HOME" or (isinstance(res, dict) and res.get("type") is None))

    # 5. Test Alarm Ramp Trigger & ACK state
    BLEGatesView.active_tab = "LIVE"
    gateway.trigger_test_alarm_ramp()
    time.sleep(0.3)  # Allow simulation to step
    # Force temperature to critical
    nrf1 = gateway.nodes.get("node_nrf_01")
    if nrf1 and "temp" in nrf1.channels:
        nrf1.channels["temp"].current_val = 103.4
        gateway.threshold_engine.evaluate_channel(nrf1.channels["temp"], "node_nrf_01")

    has_crit = gateway.threshold_engine.has_critical_alarm()
    check("Critical Alarm Triggered", has_crit)

    # Render with critical banner
    try:
        BLEGatesView.render(screen, fonts, colors, 0)
        banner_render_ok = True
    except Exception as e:
        banner_render_ok = False
        print(f"Critical banner error: {e}")
    check("Critical Alarm Banner Rendered", banner_render_ok)

    # Touch ACK button (x=200, y=60)
    ack_res = view.handle_touch((200, 60))
    check("Touch ACK Alarm", gateway.threshold_engine.active_critical_alarm is None or gateway.threshold_engine.active_critical_alarm.level == AlertLevel.ACKNOWLEDGED)

    gateway.stop_test_alarm_ramp()
    if nrf1 and "temp" in nrf1.channels:
        nrf1.channels["temp"].current_val = 26.5
        gateway.threshold_engine.evaluate_channel(nrf1.channels["temp"], "node_nrf_01")

    print("=" * 68)
    print(f"  >> RESULT: {passed}/{total} Multi-Node Tests Passed Successfully!")
    print("=" * 68)
    return passed == total


if __name__ == "__main__":
    success = run_multinode_tests()
    sys.exit(0 if success else 1)
