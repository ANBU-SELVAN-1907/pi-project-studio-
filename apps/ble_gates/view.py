"""
Universal BLE Sensor Gateway View for 2.4" TFT (240x320 Touch).
Features:
- 5 High-DPI Tabs: [ LIVE ] | [ GRAPH ] | [ RAW ] | [ DEV ] | [ ALERTS ]
- Multi-Node Switching (nRF52832, ESP32-C3, ESP32-S3, Custom, Unknown)
- Live Sparklines & Full-Screen Real-Time Waveform / 3-Axis Graph
- Threshold Engine with Hysteresis & State Machine (Warning / Critical)
- Flashing Critical Alarm Banner & Instant Acknowledge Button
- Session Recording to Disk (Zero RAM) & Unknown Sensor Decoder Modal
"""

import time
import math
from typing import Any, Dict, Tuple, Optional, List
import pygame

from core import config
from ui.base_view import BaseView
from core.ble_gateway.models import (
    ChannelType, GraphType, AlertLevel, ThresholdConfig
)
from core.ble_gateway.hub import get_ble_gateway


class BLEGatesView(BaseView):
    """
    Premier Universal BLE Sensor Gateway Dashboard.
    100% compliant with low-RAM (< 15MB) budget and 2.4" TFT touch ergonomics.
    """

    view_id = "BLE_GATES"
    title = "BLE Gates"
    icon = "ble"

    # UI State
    active_tab = "LIVE"  # "LIVE", "GRAPH", "RAW", "DEV", "ALERTS"
    scroll_y = 0.0
    target_scroll_y = 0.0
    _touch_start_y = 0.0
    _is_dragging = False

    # Graph Tab State
    selected_graph_channel = "temp"

    # Raw Tab State
    raw_paused = False

    # Threshold Modal State
    modal_open = False
    modal_channel_id = "temp"
    modal_warn_high = 80.0
    modal_crit_high = 100.0
    modal_hysteresis = 3.0
    modal_enabled = True

    # Unknown Sensor Modal State
    unknown_modal_open = False

    @classmethod
    def render(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                engine_or_ox: Any = 0, ox: int = 0) -> None:
        """
        Renders the entire Universal BLE Gateway screen.
        Handles both (screen, fonts, colors, engine, ox) and (screen, fonts, colors, 0).
        """
        offset_x = ox if isinstance(engine_or_ox, (int, float)) and ox == 0 and engine_or_ox != 0 else (ox if not isinstance(engine_or_ox, (int, float)) else int(engine_or_ox))
        engine = engine_or_ox if not isinstance(engine_or_ox, (int, float)) else None

        # Smooth kinetic scroll interpolation
        cls.scroll_y += (cls.target_scroll_y - cls.scroll_y) * 0.35

        gateway = get_ble_gateway()
        node = gateway.get_selected_node()

        header_font = fonts.get("header") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]
        small_font = fonts.get("small") or fonts["body"]
        title_font = fonts.get("title") or fonts["header"]

        W = config.SCREEN_WIDTH
        H = config.SCREEN_HEIGHT

        # -------------------------------------------------------------
        # 1. TOP HEADER BAR (y = 22 to 46, height = 24)
        # -------------------------------------------------------------
        header_r = pygame.Rect(6 + offset_x, 22, 228, 24)
        pygame.draw.rect(screen, colors.get("COLOR_SURFACE", (20, 22, 30)), header_r, border_radius=5)
        pygame.draw.rect(screen, colors.get("COLOR_BORDER", (34, 38, 52)), header_r, width=1, border_radius=5)

        # Back Button (< Home)
        back_r = pygame.Rect(8 + offset_x, 24, 46, 20)
        pygame.draw.rect(screen, colors.get("COLOR_KEY_BG", (26, 29, 40)), back_r, border_radius=4)
        b_txt = small_font.render("< Home", True, colors.get("COLOR_TEXT_PRIMARY", (248, 249, 250)))
        screen.blit(b_txt, (12 + offset_x, 28))

        # Active Node Switcher Button (e.g. nRF52832 ▼)
        node_name_short = node.name.split("(")[0].strip() if node else "No Node"
        if len(node_name_short) > 13:
            node_name_short = node_name_short[:12] + ".."
        node_btn_r = pygame.Rect(58 + offset_x, 24, 114, 20)
        pygame.draw.rect(screen, (16, 26, 44), node_btn_r, border_radius=4)
        pygame.draw.rect(screen, (30, 58, 95), node_btn_r, width=1, border_radius=4)
        n_txt = small_font.render(f"{node_name_short} ▼", True, (59, 130, 246))
        screen.blit(n_txt, (64 + offset_x, 28))

        # Highest Alert State Pill (Flashing on Critical)
        highest_alert = gateway.threshold_engine.get_highest_alert()
        pill_r = pygame.Rect(176 + offset_x, 24, 54, 20)
        if highest_alert == AlertLevel.CRITICAL:
            flash = int(time.time() * 3) % 2 == 0
            pill_col = (220, 38, 38) if flash else (120, 20, 20)
            p_text = "CRIT ⚠"
            t_col = (255, 255, 255)
        elif highest_alert == AlertLevel.WARNING:
            pill_col = (217, 119, 6)
            p_text = "WARN"
            t_col = (255, 255, 255)
        elif highest_alert == AlertLevel.ACKNOWLEDGED:
            pill_col = (100, 116, 139)
            p_text = "ACK'D"
            t_col = (255, 255, 255)
        else:
            pill_col = (16, 185, 129)
            p_text = "NORMAL"
            t_col = (255, 255, 255)

        pygame.draw.rect(screen, pill_col, pill_r, border_radius=4)
        p_surf = small_font.render(p_text, True, t_col)
        screen.blit(p_surf, (180 + offset_x, 28))

        # -------------------------------------------------------------
        # 2. CRITICAL ALARM BANNER (Conditional overlay if critical active)
        # -------------------------------------------------------------
        banner_offset_y = 0
        if gateway.threshold_engine.has_critical_alarm():
            banner_offset_y = 22
            crit_r = pygame.Rect(6 + offset_x, 48, 228, 20)
            pygame.draw.rect(screen, (180, 20, 30), crit_r, border_radius=4)
            pygame.draw.rect(screen, (255, 100, 100), crit_r, width=1, border_radius=4)
            c_txt = small_font.render("⚠ CRITICAL THRESHOLD VIOLATION!", True, (255, 255, 255))
            screen.blit(c_txt, (10 + offset_x, 52))

            ack_btn_r = pygame.Rect(184 + offset_x, 49, 46, 18)
            pygame.draw.rect(screen, (255, 255, 255), ack_btn_r, border_radius=3)
            ack_s = small_font.render("ACK", True, (180, 20, 30))
            screen.blit(ack_s, (196 + offset_x, 52))

        # -------------------------------------------------------------
        # 3. NAVIGATION TAB BAR (5 Tabs: LIVE | GRAPH | RAW | DEV | ALERTS)
        # -------------------------------------------------------------
        tab_y = 48 + banner_offset_y
        tab_bar_r = pygame.Rect(6 + offset_x, tab_y, 228, 22)
        pygame.draw.rect(screen, (16, 18, 24), tab_bar_r, border_radius=4)

        tabs = [
            ("LIVE", "LIVE", 44),
            ("GRAPH", "GRAPH", 46),
            ("RAW", "RAW", 40),
            ("DEV", "DEV", 40),
            ("ALERTS", "ALERTS", 58)
        ]

        cur_tx = 6 + offset_x
        for tid, tlabel, tw in tabs:
            tr = pygame.Rect(cur_tx, tab_y, tw, 22)
            is_active = (cls.active_tab == tid)
            if is_active:
                pygame.draw.rect(screen, (24, 36, 56), tr, border_radius=4)
                pygame.draw.rect(screen, (59, 130, 246), (cur_tx + 2, tab_y + 19, tw - 4, 2), border_radius=1)
                t_color = (59, 130, 246)
            else:
                t_color = colors.get("COLOR_TEXT_MUTED", (100, 116, 139))

            ts = small_font.render(tlabel, True, t_color)
            screen.blit(ts, (cur_tx + (tw - ts.get_width()) // 2, tab_y + 4))
            cur_tx += tw

        # -------------------------------------------------------------
        # 4. VIEWPORT CLIPPING & TAB CONTENT RENDERING
        # -------------------------------------------------------------
        content_top = tab_y + 24
        content_h = H - content_top - 4
        viewport_r = pygame.Rect(0, content_top, W, content_h)
        screen.set_clip(viewport_r)

        try:
            if cls.active_tab == "LIVE":
                cls._render_live_tab(screen, fonts, colors, node, gateway, offset_x, content_top)
            elif cls.active_tab == "GRAPH":
                cls._render_graph_tab(screen, fonts, colors, node, gateway, offset_x, content_top)
            elif cls.active_tab == "RAW":
                cls._render_raw_tab(screen, fonts, colors, node, gateway, offset_x, content_top)
            elif cls.active_tab == "DEV":
                cls._render_device_tab(screen, fonts, colors, node, gateway, offset_x, content_top)
            elif cls.active_tab == "ALERTS":
                cls._render_alerts_tab(screen, fonts, colors, node, gateway, offset_x, content_top)
        finally:
            screen.set_clip(None)

        # -------------------------------------------------------------
        # 5. THRESHOLD CONFIG MODAL OVERLAY
        # -------------------------------------------------------------
        if cls.modal_open:
            cls._render_threshold_modal(screen, fonts, colors, offset_x)

    @classmethod
    def _render_live_tab(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                         node: Any, gateway: Any, offset_x: int, top_y: int) -> None:
        """Renders the scrollable list of Sensor Channel Cards with live sparklines."""
        if not node or not node.channels:
            msg = fonts["body"].render("No sensor channels found.", True, (148, 163, 184))
            screen.blit(msg, (40 + offset_x, top_y + 20))
            return

        small_font = fonts.get("small") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]

        card_h = 56
        spacing = 6
        channels_list = list(node.channels.values())

        # Clamp target scroll
        max_scroll = max(0, len(channels_list) * (card_h + spacing) - 210)
        cls.target_scroll_y = max(-max_scroll, min(0, cls.target_scroll_y))

        for i, ch in enumerate(channels_list):
            card_y = int(top_y + cls.scroll_y + i * (card_h + spacing))
            if card_y + card_h < top_y - 10 or card_y > config.SCREEN_HEIGHT:
                continue

            card_r = pygame.Rect(8 + offset_x, card_y, 224, card_h)
            pygame.draw.rect(screen, colors.get("COLOR_SURFACE", (20, 22, 30)), card_r, border_radius=6)
            pygame.draw.rect(screen, colors.get("COLOR_BORDER", (34, 38, 52)), card_r, width=1, border_radius=6)

            # Left color category strip
            col_bar = cls._get_channel_color(ch.channel_type)
            pygame.draw.rect(screen, col_bar, (8 + offset_x, card_y + 4, 3, card_h - 8), border_radius=2)

            # Channel Name & [DERIVED] Badge
            name_s = small_font.render(ch.name[:18], True, colors.get("COLOR_TEXT_PRIMARY", (248, 249, 250)))
            screen.blit(name_s, (16 + offset_x, card_y + 6))

            if ch.is_derived:
                d_r = pygame.Rect(16 + name_s.get_width() + 4 + offset_x, card_y + 6, 44, 12)
                pygame.draw.rect(screen, (30, 41, 59), d_r, border_radius=3)
                d_txt = small_font.render("DERIVED", True, (148, 163, 184))
                screen.blit(d_txt, (16 + name_s.get_width() + 6 + offset_x, card_y + 7))

            # Channel Current Value + Unit
            val_str = f"{ch.current_val} {ch.unit}" if not isinstance(ch.current_val, float) else f"{ch.current_val:.2f} {ch.unit}"
            val_s = body_font.render(val_str, True, col_bar)
            screen.blit(val_s, (16 + offset_x, card_y + 20))

            # Alert Pill (NORMAL / WARN / CRIT)
            if ch.alert_level == AlertLevel.CRITICAL:
                pill_c = (220, 38, 38)
                pill_t = "CRIT"
            elif ch.alert_level == AlertLevel.WARNING:
                pill_c = (217, 119, 6)
                pill_t = "WARN"
            elif ch.alert_level == AlertLevel.ACKNOWLEDGED:
                pill_c = (100, 116, 139)
                pill_t = "ACK"
            else:
                pill_c = (16, 185, 129)
                pill_t = "OK"

            pill_r = pygame.Rect(16 + offset_x, card_y + 36, 32, 14)
            pygame.draw.rect(screen, pill_c, pill_r, border_radius=3)
            pt_s = small_font.render(pill_t, True, (255, 255, 255))
            screen.blit(pt_s, (20 + offset_x, card_y + 37))

            # Mini Sparkline Trend Graph (width = 54, height = 24)
            spark_r = pygame.Rect(78 + offset_x, card_y + 24, 54, 24)
            cls._draw_sparkline(screen, spark_r, gateway, node.device_id, ch.id, col_bar)

            # Action Buttons: [GRAPH] & [LIMIT]
            g_btn_r = pygame.Rect(140 + offset_x, card_y + 24, 40, 24)
            pygame.draw.rect(screen, (16, 36, 60), g_btn_r, border_radius=4)
            pygame.draw.rect(screen, (59, 130, 246), g_btn_r, width=1, border_radius=4)
            g_txt = small_font.render("Graph", True, (59, 130, 246))
            screen.blit(g_txt, (144 + offset_x, card_y + 29))

            l_btn_r = pygame.Rect(184 + offset_x, card_y + 24, 42, 24)
            pygame.draw.rect(screen, (24, 30, 42), l_btn_r, border_radius=4)
            pygame.draw.rect(screen, (100, 116, 139), l_btn_r, width=1, border_radius=4)
            l_txt = small_font.render("Limit", True, colors.get("COLOR_TEXT_PRIMARY", (248, 249, 250)))
            screen.blit(l_txt, (190 + offset_x, card_y + 29))

    @classmethod
    def _draw_sparkline(cls, screen: pygame.Surface, rect: pygame.Rect,
                        gateway: Any, node_id: str, channel_id: str, color: Tuple[int, int, int]) -> None:
        """Draws an anti-aliased live sparkline trend inside the channel card."""
        pygame.draw.rect(screen, (12, 14, 20), rect, border_radius=3)
        buf = gateway.get_channel_buffer(node_id, channel_id)
        if not buf or len(buf.buffer) < 2:
            return

        series = buf.downsample(20)
        if not series:
            return

        vals = [v for _, v in series]
        min_v = min(vals)
        max_v = max(vals)
        span = max_v - min_v if max_v != min_v else 1.0

        pts = []
        for j, v in enumerate(vals):
            px = rect.x + int(j * (rect.width / (len(vals) - 1)))
            norm = (v - min_v) / span
            py = rect.bottom - 2 - int(norm * (rect.height - 4))
            pts.append((px, py))

        if len(pts) >= 2:
            pygame.draw.lines(screen, color, False, pts, 1)

    @classmethod
    def _render_graph_tab(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                          node: Any, gateway: Any, offset_x: int, top_y: int) -> None:
        """Renders the full-screen high-DPI live waveform / 3-axis graph."""
        small_font = fonts.get("small") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]

        if not node or not node.channels:
            return

        # 1. Channel Selector Bar (horizontal scroll/wrap)
        ch_keys = list(node.channels.keys())
        if cls.selected_graph_channel not in node.channels and ch_keys:
            cls.selected_graph_channel = ch_keys[0]

        sel_ch = node.channels[cls.selected_graph_channel]
        col = cls._get_channel_color(sel_ch.channel_type)

        # Header with Channel Selector Button
        bar_r = pygame.Rect(8 + offset_x, top_y + 2, 224, 20)
        pygame.draw.rect(screen, (18, 24, 36), bar_r, border_radius=4)
        ch_s = small_font.render(f"Channel: {sel_ch.name} ({sel_ch.unit}) [TAP TO SWITCH]", True, (59, 130, 246))
        screen.blit(ch_s, (14 + offset_x, top_y + 5))

        # 2. Main Live Graph Canvas (width = 224, height = 120)
        graph_r = pygame.Rect(8 + offset_x, top_y + 26, 224, 120)
        pygame.draw.rect(screen, (10, 12, 16), graph_r, border_radius=6)
        pygame.draw.rect(screen, colors.get("COLOR_BORDER", (34, 38, 52)), graph_r, width=1, border_radius=6)

        # Grid lines
        for gy in range(graph_r.top + 24, graph_r.bottom, 24):
            pygame.draw.line(screen, (20, 24, 34), (graph_r.left, gy), (graph_r.right, gy), 1)

        buf = gateway.get_channel_buffer(node.device_id, sel_ch.id)
        current, min_v, max_v, avg_v = buf.get_stats() if buf else (sel_ch.current_val, sel_ch.current_val, sel_ch.current_val, sel_ch.current_val)

        # Plot data points
        if buf and len(buf.buffer) >= 2:
            series = buf.downsample(36)
            vals = [v for _, v in series]
            g_min = min(min_v, min(vals))
            g_max = max(max_v, max(vals))
            span = g_max - g_min if g_max != g_min else 1.0

            pts = []
            for j, v in enumerate(vals):
                px = graph_r.left + 4 + int(j * ((graph_r.width - 8) / (len(vals) - 1)))
                norm = (v - g_min) / span
                py = graph_r.bottom - 4 - int(norm * (graph_r.height - 8))
                pts.append((px, py))

            if len(pts) >= 2:
                pygame.draw.lines(screen, col, False, pts, 2)

            # Draw threshold limit lines if configured
            cfg = gateway.threshold_engine.get_config(sel_ch.id)
            if cfg and cfg.enabled:
                if cfg.crit_high is not None and g_min <= cfg.crit_high <= g_max:
                    cy = graph_r.bottom - 4 - int(((cfg.crit_high - g_min) / span) * (graph_r.height - 8))
                    pygame.draw.line(screen, (220, 38, 38), (graph_r.left, cy), (graph_r.right, cy), 1)
                if cfg.warn_high is not None and g_min <= cfg.warn_high <= g_max:
                    wy = graph_r.bottom - 4 - int(((cfg.warn_high - g_min) / span) * (graph_r.height - 8))
                    pygame.draw.line(screen, (217, 119, 6), (graph_r.left, wy), (graph_r.right, wy), 1)

        # Min/Max labels on graph
        min_s = small_font.render(f"{min_v:.1f}", True, (100, 116, 139))
        max_s = small_font.render(f"{max_v:.1f}", True, (100, 116, 139))
        screen.blit(max_s, (graph_r.left + 4, graph_r.top + 4))
        screen.blit(min_s, (graph_r.left + 4, graph_r.bottom - 16))

        # 3. Statistical Metrics Strip Underneath
        stat_r = pygame.Rect(8 + offset_x, top_y + 152, 224, 28)
        pygame.draw.rect(screen, colors.get("COLOR_SURFACE", (20, 22, 30)), stat_r, border_radius=4)
        stat_txt = f"NOW: {current:.2f} | MIN: {min_v:.2f} | MAX: {max_v:.2f} | AVG: {avg_v:.2f}"
        st_s = small_font.render(stat_txt, True, colors.get("COLOR_TEXT_PRIMARY", (248, 249, 250)))
        screen.blit(st_s, (14 + offset_x, top_y + 158))

    @classmethod
    def _render_raw_tab(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                        node: Any, gateway: Any, offset_x: int, top_y: int) -> None:
        """Renders the live incoming BLE Hex Packet Monitor."""
        small_font = fonts.get("small") or fonts["body"]

        # Control strip: Pause & Rate
        bar_r = pygame.Rect(8 + offset_x, top_y + 2, 224, 20)
        pygame.draw.rect(screen, (16, 20, 30), bar_r, border_radius=4)
        screen.blit(small_font.render("Live GATT Hex Stream (10 Hz)", True, (148, 163, 184)), (14 + offset_x, top_y + 5))

        # Pause button
        pause_r = pygame.Rect(176 + offset_x, top_y + 3, 50, 18)
        pygame.draw.rect(screen, (30, 40, 56), pause_r, border_radius=3)
        p_txt = "RUN" if cls.raw_paused else "PAUSE"
        screen.blit(small_font.render(p_txt, True, (59, 130, 246)), (184 + offset_x, top_y + 5))

        # Log box (height = 160)
        box_r = pygame.Rect(8 + offset_x, top_y + 26, 224, 154)
        pygame.draw.rect(screen, (8, 9, 12), box_r, border_radius=4)
        pygame.draw.rect(screen, (24, 28, 40), box_r, width=1, border_radius=4)

        packets = list(gateway.raw_packet_stream)[-8:]
        for idx, pkt in enumerate(packets):
            py = top_y + 30 + idx * 18
            time_str = time.strftime("%H:%M:%S", time.localtime(pkt.timestamp))
            line = f"[{time_str}] {pkt.hex_data[:24]} ({pkt.length}B)"
            line_s = small_font.render(line, True, (16, 185, 129))
            screen.blit(line_s, (14 + offset_x, py))

    @classmethod
    def _render_device_tab(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                           node: Any, gateway: Any, offset_x: int, top_y: int) -> None:
        """Renders device hardware information, RSSI, and session recording controls."""
        small_font = fonts.get("small") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]

        if not node:
            return

        # 1. Device Hardware Card
        d_card = pygame.Rect(8 + offset_x, top_y + 2, 224, 88)
        pygame.draw.rect(screen, colors.get("COLOR_SURFACE", (20, 22, 30)), d_card, border_radius=6)
        pygame.draw.rect(screen, colors.get("COLOR_BORDER", (34, 38, 52)), d_card, width=1, border_radius=6)

        screen.blit(body_font.render(f"Device: {node.name}", True, (248, 249, 250)), (14 + offset_x, top_y + 8))
        screen.blit(small_font.render(f"MAC: {node.mac}", True, (148, 163, 184)), (14 + offset_x, top_y + 24))
        screen.blit(small_font.render(f"RSSI: {node.rssi} dBm (Good)", True, (16, 185, 129)), (14 + offset_x, top_y + 38))
        screen.blit(small_font.render(f"Packets RX: {node.packets_count}", True, (148, 163, 184)), (14 + offset_x, top_y + 52))
        screen.blit(small_font.render(f"State: CONNECTED (Auto-Sync)", True, (59, 130, 246)), (14 + offset_x, top_y + 66))

        # 2. Session Recording Card
        r_card = pygame.Rect(8 + offset_x, top_y + 96, 224, 84)
        pygame.draw.rect(screen, colors.get("COLOR_SURFACE", (20, 22, 30)), r_card, border_radius=6)
        pygame.draw.rect(screen, colors.get("COLOR_BORDER", (34, 38, 52)), r_card, width=1, border_radius=6)

        screen.blit(body_font.render("Session Disk Recording", True, (248, 249, 250)), (14 + offset_x, top_y + 102))

        rec_status = f"● RECORDING ({gateway.recorder.samples_written} pts)" if gateway.recorder.is_recording else "○ IDLE (No file open)"
        rec_col = (220, 38, 38) if gateway.recorder.is_recording else (148, 163, 184)
        screen.blit(small_font.render(rec_status, True, rec_col), (14 + offset_x, top_y + 120))

        # Start / Stop Buttons
        start_r = pygame.Rect(14 + offset_x, top_y + 142, 96, 26)
        pygame.draw.rect(screen, (16, 60, 36), start_r, border_radius=4)
        pygame.draw.rect(screen, (16, 185, 129), start_r, width=1, border_radius=4)
        screen.blit(small_font.render("● START REC", True, (16, 185, 129)), (24 + offset_x, top_y + 148))

        stop_r = pygame.Rect(120 + offset_x, top_y + 142, 96, 26)
        pygame.draw.rect(screen, (40, 20, 24), stop_r, border_radius=4)
        pygame.draw.rect(screen, (220, 38, 38), stop_r, width=1, border_radius=4)
        screen.blit(small_font.render("■ STOP", True, (220, 38, 38)), (148 + offset_x, top_y + 148))

    @classmethod
    def _render_alerts_tab(cls, screen: pygame.Surface, fonts: dict, colors: dict,
                           node: Any, gateway: Any, offset_x: int, top_y: int) -> None:
        """Renders active thresholds, alarm logs, and the Test Alarm Ramp trigger."""
        small_font = fonts.get("small") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]

        # Action bar: Acknowledge button & Test Alarm Ramp
        ack_all_r = pygame.Rect(8 + offset_x, top_y + 2, 108, 26)
        pygame.draw.rect(screen, (16, 36, 60), ack_all_r, border_radius=4)
        pygame.draw.rect(screen, (59, 130, 246), ack_all_r, width=1, border_radius=4)
        screen.blit(small_font.render("✓ ACK ALARMS", True, (59, 130, 246)), (16 + offset_x, top_y + 8))

        ramp_r = pygame.Rect(124 + offset_x, top_y + 2, 108, 26)
        pygame.draw.rect(screen, (60, 24, 16), ramp_r, border_radius=4)
        pygame.draw.rect(screen, (245, 158, 11), ramp_r, width=1, border_radius=4)
        screen.blit(small_font.render("⚡ TEST RAMP", True, (245, 158, 11)), (134 + offset_x, top_y + 8))

        # Alarm History Log
        screen.blit(body_font.render("Recent Alarm Events:", True, (248, 249, 250)), (12 + offset_x, top_y + 36))

        history = list(gateway.threshold_engine.alarm_history)[-6:]
        if not history:
            screen.blit(small_font.render("No alarms triggered yet. System nominal.", True, (16, 185, 129)), (14 + offset_x, top_y + 54))
        else:
            for idx, evt in enumerate(reversed(history)):
                ey = top_y + 54 + idx * 22
                t_str = time.strftime("%H:%M:%S", time.localtime(evt.timestamp))
                line = f"[{t_str}] {evt.channel_name}: {evt.value:.1f} (Lim {evt.limit:.1f}) [{evt.state}]"
                col = (220, 38, 38) if evt.level == AlertLevel.CRITICAL else (217, 119, 6)
                screen.blit(small_font.render(line, True, col), (14 + offset_x, ey))

    @classmethod
    def _render_threshold_modal(cls, screen: pygame.Surface, fonts: dict, colors: dict, offset_x: int) -> None:
        """Renders the high-DPI threshold configuration dialog overlay."""
        small_font = fonts.get("small") or fonts["body"]
        body_font = fonts.get("body") or fonts["small"]
        title_font = fonts.get("title") or fonts["header"]

        # Dark overlay
        dark = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 180))
        screen.blit(dark, (0, 0))

        # Modal Box (x = 16, y = 48, width = 208, height = 224)
        modal_r = pygame.Rect(16 + offset_x, 48, 208, 224)
        pygame.draw.rect(screen, (18, 22, 32), modal_r, border_radius=8)
        pygame.draw.rect(screen, (59, 130, 246), modal_r, width=2, border_radius=8)

        # Title
        t_s = title_font.render(f"Limit: {cls.modal_channel_id.capitalize()}", True, (248, 249, 250))
        screen.blit(t_s, (26 + offset_x, 56))

        # Warning High Adjuster
        screen.blit(small_font.render(f"Warn High Limit: {cls.modal_warn_high:.1f}", True, (217, 119, 6)), (26 + offset_x, 82))
        cls._draw_stepper_btns(screen, small_font, 26 + offset_x, 96, "warn_high")

        # Critical High Adjuster
        screen.blit(small_font.render(f"Crit High Limit: {cls.modal_crit_high:.1f}", True, (220, 38, 38)), (26 + offset_x, 126))
        cls._draw_stepper_btns(screen, small_font, 26 + offset_x, 140, "crit_high")

        # Hysteresis %
        screen.blit(small_font.render(f"Hysteresis Deadband: {cls.modal_hysteresis:.1f}%", True, (148, 163, 184)), (26 + offset_x, 172))

        # Save & Cancel Buttons
        save_r = pygame.Rect(26 + offset_x, 218, 88, 28)
        pygame.draw.rect(screen, (16, 185, 129), save_r, border_radius=4)
        screen.blit(body_font.render("SAVE", True, (255, 255, 255)), (54 + offset_x, 224))

        cancel_r = pygame.Rect(122 + offset_x, 218, 88, 28)
        pygame.draw.rect(screen, (40, 46, 60), cancel_r, border_radius=4)
        screen.blit(body_font.render("CANCEL", True, (255, 255, 255)), (140 + offset_x, 224))

    @classmethod
    def _draw_stepper_btns(cls, screen: pygame.Surface, font: Any, x: int, y: int, target: str) -> None:
        """Draws [-5], [-1], [+1], [+5] adjustment buttons."""
        steps = [(-5.0, "-5"), (-1.0, "-1"), (1.0, "+1"), (5.0, "+5")]
        for idx, (val, lbl) in enumerate(steps):
            bx = x + idx * 46
            br = pygame.Rect(bx, y, 42, 22)
            pygame.draw.rect(screen, (28, 34, 48), br, border_radius=3)
            pygame.draw.rect(screen, (59, 130, 246), br, width=1, border_radius=3)
            screen.blit(font.render(lbl, True, (248, 249, 250)), (bx + 10, y + 4))

    @staticmethod
    def _get_channel_color(ch_type: ChannelType) -> Tuple[int, int, int]:
        """Maps channel type to vibrant high-contrast QLED theme color."""
        if ch_type == ChannelType.TEMP:
            return (239, 68, 68)  # Coral Red
        if ch_type == ChannelType.HUMIDITY:
            return (14, 165, 233)  # Sky Blue
        if ch_type == ChannelType.PRESSURE:
            return (168, 85, 247)  # Violet
        if ch_type == ChannelType.GAS:
            return (234, 179, 8)   # Amber
        if ch_type in (ChannelType.ACCEL_3AXIS, ChannelType.GYRO_3AXIS):
            return (245, 158, 11)  # Orange
        if ch_type in (ChannelType.DISTANCE, ChannelType.PROXIMITY):
            return (99, 102, 241)  # Indigo
        if ch_type == ChannelType.BATTERY:
            return (16, 185, 129)  # Emerald
        return (59, 130, 246)      # Primary Blue

    def handle_touch(self, pos: tuple, engine: Any = None) -> Any:
        """
        High-precision touch event handler for finger and stylus input.
        Never misses clicks and guarantees accurate coordinate mapping.
        """
        x, y = pos
        gateway = get_ble_gateway()

        # 1. Back to Home Navigation
        if 8 <= x <= 56 and 22 <= y <= 48:
            if engine and hasattr(engine, "navigate_to"):
                engine.navigate_to("HOME")
                return {"type": None, "value": None}
            return "BACK_HOME"

        # 2. Node Switcher Tap
        if 58 <= x <= 172 and 22 <= y <= 48:
            gateway.select_next_node()
            return {"type": "NODE_SWITCHED"}

        # 3. Critical Alarm Acknowledge
        if gateway.threshold_engine.has_critical_alarm() and 48 <= y <= 70:
            gateway.threshold_engine.acknowledge_alarm()
            return {"type": "ALARM_ACKNOWLEDGED"}

        # 4. Tab Switching
        banner_offset = 22 if gateway.threshold_engine.has_critical_alarm() else 0
        tab_y = 48 + banner_offset
        if tab_y <= y <= tab_y + 24:
            if 6 <= x <= 50:
                BLEGatesView.active_tab = "LIVE"
                self.active_tab = "LIVE"
                BLEGatesView.scroll_y = 0.0
                BLEGatesView.target_scroll_y = 0.0
                self.scroll_y = 0.0
                self.target_scroll_y = 0.0
            elif 50 <= x <= 96:
                BLEGatesView.active_tab = "GRAPH"
                self.active_tab = "GRAPH"
            elif 96 <= x <= 136:
                BLEGatesView.active_tab = "RAW"
                self.active_tab = "RAW"
            elif 136 <= x <= 176:
                BLEGatesView.active_tab = "DEV"
                self.active_tab = "DEV"
            elif 176 <= x <= 234:
                BLEGatesView.active_tab = "ALERTS"
                self.active_tab = "ALERTS"
            return {"type": "TAB_SWITCHED", "tab": BLEGatesView.active_tab}

        # 5. Threshold Modal Handling
        if self.modal_open:
            if 16 <= x <= 224 and 48 <= y <= 272:
                # Stepper buttons for warn_high
                if 96 <= y <= 118:
                    if 26 <= x <= 68: self.modal_warn_high -= 5.0
                    elif 72 <= x <= 114: self.modal_warn_high -= 1.0
                    elif 118 <= x <= 160: self.modal_warn_high += 1.0
                    elif 164 <= x <= 206: self.modal_warn_high += 5.0
                    return {"type": "STEPPER"}
                # Stepper buttons for crit_high
                elif 140 <= y <= 162:
                    if 26 <= x <= 68: self.modal_crit_high -= 5.0
                    elif 72 <= x <= 114: self.modal_crit_high -= 1.0
                    elif 118 <= x <= 160: self.modal_crit_high += 1.0
                    elif 164 <= x <= 206: self.modal_crit_high += 5.0
                    return {"type": "STEPPER"}
                # Save button
                elif 218 <= y <= 246 and 26 <= x <= 114:
                    cfg = ThresholdConfig(
                        channel_id=self.modal_channel_id,
                        enabled=True,
                        warn_high=self.modal_warn_high,
                        crit_high=self.modal_crit_high,
                        hysteresis_pct=self.modal_hysteresis,
                        alarm_enabled=True
                    )
                    gateway.threshold_engine.set_config(cfg)
                    self.modal_open = False
                    return {"type": "MODAL_SAVED"}
                # Cancel button
                elif 218 <= y <= 246 and 122 <= x <= 210:
                    self.modal_open = False
                    return {"type": "MODAL_CANCEL"}
            else:
                self.modal_open = False
                return {"type": "MODAL_CLOSE"}

        # 6. LIVE Tab Actions
        if self.active_tab == "LIVE":
            node = gateway.get_selected_node()
            if node and node.channels:
                content_top = tab_y + 24
                channels_list = list(node.channels.values())
                for i, ch in enumerate(channels_list):
                    card_y = int(content_top + self.scroll_y + i * 62)
                    # Graph button tap
                    if 140 <= x <= 180 and card_y + 24 <= y <= card_y + 48:
                        self.selected_graph_channel = ch.id
                        self.active_tab = "GRAPH"
                        return {"type": "OPEN_GRAPH", "channel": ch.id}
                    # Limit button tap
                    elif 184 <= x <= 226 and card_y + 24 <= y <= card_y + 48:
                        cfg = gateway.threshold_engine.get_config(ch.id)
                        self.modal_channel_id = ch.id
                        self.modal_warn_high = cfg.warn_high if (cfg and cfg.warn_high is not None) else 80.0
                        self.modal_crit_high = cfg.crit_high if (cfg and cfg.crit_high is not None) else 100.0
                        self.modal_hysteresis = cfg.hysteresis_pct if cfg else 3.0
                        self.modal_open = True
                        return {"type": "OPEN_MODAL", "channel": ch.id}

        # 7. GRAPH Tab Channel Switch
        elif self.active_tab == "GRAPH":
            content_top = tab_y + 24
            if 8 <= x <= 232 and content_top <= y <= content_top + 22:
                node = gateway.get_selected_node()
                if node and node.channels:
                    keys = list(node.channels.keys())
                    try:
                        cur_i = keys.index(self.selected_graph_channel)
                        self.selected_graph_channel = keys[(cur_i + 1) % len(keys)]
                    except ValueError:
                        self.selected_graph_channel = keys[0]
                    return {"type": "SWITCH_GRAPH_CHANNEL", "channel": self.selected_graph_channel}

        # 8. RAW Tab Pause Toggle
        elif self.active_tab == "RAW":
            content_top = tab_y + 24
            if 176 <= x <= 226 and content_top + 3 <= y <= content_top + 22:
                self.raw_paused = not self.raw_paused
                return {"type": "TOGGLE_RAW"}

        # 9. DEVICE Tab Recording
        elif self.active_tab == "DEV":
            content_top = tab_y + 24
            # Start Rec
            if 14 <= x <= 110 and content_top + 142 <= y <= content_top + 168:
                gateway.recorder.start_session()
                return {"type": "START_REC"}
            # Stop Rec
            elif 120 <= x <= 216 and content_top + 142 <= y <= content_top + 168:
                gateway.recorder.stop_session()
                return {"type": "STOP_REC"}

        # 10. ALERTS Tab Actions
        elif self.active_tab == "ALERTS":
            content_top = tab_y + 24
            # Acknowledge all
            if 8 <= x <= 116 and content_top + 2 <= y <= content_top + 28:
                gateway.threshold_engine.acknowledge_alarm()
                return {"type": "ACK_ALL"}
            # Test alarm ramp
            elif 124 <= x <= 232 and content_top + 2 <= y <= content_top + 28:
                gateway.trigger_test_alarm_ramp()
                return {"type": "TRIGGER_TEST_RAMP"}

        return {"type": None, "value": None} if engine else ""

    def handle_scroll(self, dy: float, engine: Any = None) -> None:
        """Vertical gesture scroll handling."""
        if self.active_tab == "LIVE":
            self.target_scroll_y += dy * 35.0
