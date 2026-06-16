import pygame
from constants import *

# Helpers:

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def draw_rounded_rect(surf, color, rect, radius = CARD_RADIUS, border = 0, border_color = None):
    pygame.draw.rect(surf, color, rect, border_radius = radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius = radius)

def bar_color(pct: float, reverse = False):
    if reverse:
        pct = 100 - pct
    if pct > 60:
        return ACCENT_GREEN
    elif pct > 30:
        return ACCENT_YELLOW
    else:
        return ACCENT_RED
        
# Font cache:

class Fonts:
    _cache = {}

    @classmethod
    def get(cls, size: int, bold = False):
        key = (size, bold)
        if key not in cls._cache:
            try:
                cls._cache[key] = pygame.font.SysFont("segoeui", size, bold = bold)
            except Exception:
                cls._cache[key] = pygame.font.Font(None, size)
        return cls._cache[key]
    
# Individual panel drawers:

class DashboardUI:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.W = screen.get_width()
        self.H = screen.get_height()

        # Rects:
        self.topbar_rect = pygame.Rect(0, 0, self.W, TOPBAR_HEIGHT)
        self.sidebar_rect = pygame.Rect(0, TOPBAR_HEIGHT, SIDEBAR_WIDTH, self.H - TOPBAR_HEIGHT)
        self.main_rect = pygame.Rect(SIDEBAR_WIDTH, TOPBAR_HEIGHT, self.W - SIDEBAR_WIDTH, self.H - TOPBAR_HEIGHT)

        # State for popup and rename:
        self.show_rename_box = False
        self.rename_text = ""
        self.show_settings_panel = False
        self.sample_input_text = "" 
        self.upload_input_text = ""
        self.active_input = None 

        # Event popup:
        self.show_event_popup = False

        # Feedback flash:
        self._feedback_msg = ""
        self._feedback_timer = 0.0
        self._feedback_color = ACCENT_GREEN

        # Log Scroll:
        self.log_scroll = 0

        # Clickable rects:
        self._btn_rects: dict = {}

    # Public entry:

    def draw(self, node, speed_index: int):
        s = self.screen
        s.fill(BG_DARK)

        self._draw_topbar(node, speed_index)
        self._draw_sidebar(node)
        self._draw_main(node)

        # Popups on top:
        if node.events.pending_popup and not node.events.pending_popup.acknowledged:
            self._draw_event_popup(node, node.events.pending_popup)
        elif self.show_settings_panel:
            self._draw_settings_panel(node)
        elif self.show_rename_box:
            self._draw_rename_box(node)

        if node.game_over:
            self._draw_game_over(node)

        # Feedback flash:
        if self._feedback_timer > 0:
            self._draw_feedback()
            self._feedback_timer -= 1

    def _btn(self, key, rect):
        self._btn_rects[key] = rect
        return rect
    
    # Top bar:

    def _draw_topbar(self, node, speed_index):
        s = self.screen
        draw_rounded_rect(s, BG_PANEL, self.topbar_rect, radius = 0)
        pygame.draw.line(s, BORDER_COLOR, (0, TOPBAR_HEIGHT - 1), (self.W, TOPBAR_HEIGHT - 1))

        # Logo / title:
        f_big = Fonts.get(20, bold = True)
        f_small = Fonts.get(13)
        s.blit(f_big.render("ESP32:", True, ACCENT_BLUE), (16, 10))
        s.blit(f_big.render(" Deployed", True, TEXT_PRIMARY), (16 + f_big.size("ESP32:")[0], 10))

        # Node name:
        name_surf = Fonts.get(14, bold = True).render(f"[EDIT] {node.name}", True, ACCENT_YELLOW)
        name_rect = name_surf.get_rect(midleft = (220, TOPBAR_HEIGHT // 2))
        s.blit(name_surf, name_rect)
        self._btn("rename", name_rect.inflate(8, 6))

        # Status pill:
        status_color = STATUS_ONLINE if node.status_text == "ONLINE" else STATUS_SLEEPING
        pill = pygame.Rect(self.W // 2 - 50, 16, 100, 26)
        draw_rounded_rect(s, status_color + (40,) if len(status_color) == 3 else status_color, pill, radius = 13)
        pygame.draw.rect(s, status_color, pill, 1, border_radius = 13)
        status_surf = Fonts.get(13, bold = True).render(node.status_text, True, status_color)
        s.blit(status_surf, status_surf.get_rect(center = pill.center))

        # Day / Time:
        time_txt = f"Day {node.day} {node.time_string()}"
        daytime_flag = "☀️ Day" if node._is_daytime() else "🌙 Night"
        s.blit(Fonts.get(15, bold = True).render(time_txt, True, TEXT_PRIMARY), (self.W - 310, 10))
        s.blit(Fonts.get(12).render(daytime_flag, True, TEXT_SECONDARY), (self.W - 310, 30))

        # Speen controls:
        speeds = TIME_SPEEDS
        bx = self.W - 145
        s.blit(Fonts.get(11).render("SPEED", True, TEXT_MUTED), (bx, 8))
        for i, sp in enumerate(speeds):
            br = pygame.Rect(bx + i * 22, 22, 20, 18)
            active = (i == speed_index)
            draw_rounded_rect(s, ACCENT_BLUE if active else BG_CARD, br, radius = 4)
            lbl = f"{int(sp)}x" if sp >= 1 else "½x"
            c = TEXT_WHITE if active else TEXT_SECONDARY
            sv = Fonts.get(10).render(lbl, True, c)
            s.blit(sv, sv.get_rect(center = br.center))
            self._btn(f"speed_{i}", br)

    
    # Sidebar:

    def _draw_sidebar(self, node):
        s = self.screen
        draw_rounded_rect(s, BG_PANEL, self.sidebar_rect, radius = 0)
        pygame.draw.line(s, BORDER_COLOR, (SIDEBAR_WIDTH - 1, TOPBAR_HEIGHT), (SIDEBAR_WIDTH - 1, self.H))

        y = TOPBAR_HEIGHT + 14
        P = CARD_PADDING

        # Battery:
        y = self._section_header(s, "BATTERY", y, ACCENT_GREEN)
        bat_pct = node.battery_percent()
        y = self._big_stat(s, f"{bat_pct:.1f}%", "charge remaining", y, bar_color(bat_pct))
        y = self._progress_bar(s, bat_pct, bar_color(bat_pct), y)
        y = self._label_row(s, "Capacity", f"{node._effective_max_battery():.0f} units", y)
        y += 10

        # Storage:
        y = self._section_header(s, "STORAGE", y, ACCENT_ORANGE)
        sto_pct = node.storage_percent()
        y = self._big_stat(s, f"{node.storage_used:.0f} MB", f"of {node.storage_max} MB", y, bar_color(sto_pct, reverse = True))
        y += 10

        # Data Quality:
        y = self._section_header(s, "DATA QUALITY", y, ACCENT_PURPLE)
        y = self._big_stat(s, f"{node.data_quality:.1f}", "/ 100", y, bar_color(node.data_quality))
        y += 10

        # Credits:
        y = self._section_header(s, "CREDITS", y, ACCENT_YELLOW)
        y = self._big_stat(s, f"{node.credits:.2f}", "credits", y, ACCENT_YELLOW)
        y += 10

        # Solar input:
        y = self._section_header(s, "SOLAR INPUT", y, ACCENT_YELLOW)
        solar = node.solar_input_now()
        weather_icon = node.weather.get_icon()
        weather_color = node.weather.get_color()
        y = self._big_stat(s, f"{solar:.2f}", "units/hr", y, ACCENT_YELLOW)
        wsurf = Fonts.get(13).render(f"{weather_icon}, {node.weather.current}", True, weather_color)
        s.blit(wsurf, (P + 10, y))
        y += 22

        y+= 4

        # Sleep toggle button:
        sleep_lbl = "Wake Node" if node.sleeping else "Put to Sleep"
        sleep_col = ACCENT_PURPLE if node.sleeping else ACCENT_BLUE
        sleep_rect = pygame.Rect(P + 4, y, SIDEBAR_WIDTH - P * 2 - 8, 32)
        draw_rounded_rect(s, sleep_col, sleep_rect, radius = 7)
        sv = Fonts.get(13, bold = True).render(sleep_lbl, True, TEXT_WHITE)
        s.blit(sv, sv.get_rect(center = sleep_rect.center))
        self._btn("sleep_toggle", sleep_rect)
        y += 40

        # Settings button:
        stg_rect = pygame.Rect(P + 4, y, SIDEBAR_WIDTH - P * 2 -8, 32)
        draw_rounded_rect(s, BG_CARD, stg_rect, radius = 7, border = 1, border_color = BORDER_BRIGHT)
        sv2 = Fonts.get(13, bold = True).render("[SET] Settings", True, TEXT_PRIMARY)
        s.blit(sv2, sv2.get_rect(center = stg_rect.center))
        self._btn("settings", stg_rect)
        y += 40

        # Quit button:
        quit_rect = pygame.Rect(P + 4, y, SIDEBAR_WIDTH - P * 2 - 8, 32)
        draw_rounded_rect(s, (60, 20, 20), quit_rect, radius = 7, border = 1, border_color = ACCENT_RED)
        qv = Fonts.get(13, bold = True).render("Quit Game", True, ACCENT_RED)
        s.blit(qv, qv.get_rect(center = quit_rect.center))
        self._btn("quit", quit_rect)
        y += 40

        # Active events indicator:
        if node.events.active_events:
            evt_rect = pygame.Rect(P + 4, y, SIDEBAR_WIDTH - P * 2 - 8, 32)
            draw_rounded_rect(s, (80, 30, 20), evt_rect, radius = 7, border = 1, border_color = ACCENT_RED)
            ec = len(node.events.active_events)
            ev = Fonts.get(13, bold = True).render(f"[!] {ec} Active Event{'s' if ec > 1 else ''}", True, ACCENT_RED)
            s.blit(ev, ev.get_rect(center = evt_rect.center))
            self._btn("events_panel", evt_rect)

    # Main area:

    def _draw_main(self, node):
        s = self.screen
        mx = self.main_rect.x
        mw = self.main_rect.width
        P = CARD_PADDING

        # Layout two columns:
        half = (mw - P * 3) // 2
        col1_x = mx + P
        col2_x = mx + P * 2 + half

        y_top = TOPBAR_HEIGHT + P

        # Upgrades card:
        card_h = 220
        self._draw_upgrades_card(s, pygame.Rect(col1_x, y_top, half, card_h), node)

        # Stats card:
        self._draw_stats_card(s, pygame.Rect(col2_x, y_top, half, card_h), node)

        # Event log card:
        log_y = y_top + card_h + P
        log_h = self.H - log_y - P 
        self._draw_log_card(s, pygame.Rect(col1_x, log_y, mw - P * 2, log_h), node)

    def _draw_upgrades_card(self, s, rect, node):
        draw_rounded_rect(s, BG_CARD, rect, radius = CARD_RADIUS, border = 1, border_color = BORDER_COLOR)
        x, y = rect.x + CARD_PADDING, rect.y + CARD_PADDING 
        s.blit(Fonts.get(13, bold = True).render("UPGRADES", True, TEXT_MUTED), (x, y))
        y += 22

        def upgrade_row(label, level, upgrade_fn_key, cost):
            nonlocal y
            # Level dots:
            surf = Fonts.get(12).render(label, True, TEXT_SECONDARY)
            s.blit(surf, (x, y))
            for i in range(4):
                dot = pygame.Rect(x + 95 + i * 16, y +3, 10, 10)
                filled = (i < level)
                pygame.draw.rect(s, ACCENT_BLUE if filled else BG_PANEL, dot, border_radius = 3)
                if not filled:
                    pygame.draw.rect(s, BORDER_COLOR, dot, 1, border_radius = 3)
            
            # Upgrade button:
            if level < 4:
                label_txt = f"↑ L{level + 1} {cost} credits"
                btn_w = 105
                btn_r = pygame.Rect(rect.right - CARD_PADDING - btn_w, y - 2, btn_w, 22)
                has_credits = node.credits >= cost
                btn_col = ACCENT_GREEN if has_credits else BG_PANEL 
                draw_rounded_rect(s, btn_col, btn_r, radius = 5)
                lbl_s = Fonts.get(11, bold = True).render(label_txt, True, TEXT_WHITE if has_credits else TEXT_MUTED)
                s.blit(lbl_s, lbl_s.get_rect(center = btn_r.center))
                self._btn(upgrade_fn_key, btn_r)
            else:
                done = Fonts.get(11).render("MAX", True, ACCENT_GREEN)
                s.blit(done, (rect.right - CARD_PADDING - 30, y))
            y += 30

        from constants import UPGRADE_COSTS
        upgrade_row("Battery", node.battery_level, "upg_battery", UPGRADE_COSTS["battery"][node.battery_level] if node.battery_level < 4 else 0)
        upgrade_row("Solar Panel", node.solar_level, "upg_solar", UPGRADE_COSTS["solar"][node.solar_level] if node.solar_level < 4 else 0)
        upgrade_row("Antenna", node.antenna_level, "upg_antenna", UPGRADE_COSTS["antenna"][node.antenna_level] if node.antenna_level < 4 else 0)

        y += 4
        # Upload success rate display:
        from constants import ANTENNA_UPLOAD_SUCCESS
        ur = ANTENNA_UPLOAD_SUCCESS[node.antenna_level - 1] * 100
        ep = node.events.total_upload_penalty() * 100
        effective_ur = max(0, ur - ep)
        info_txt = (f"Upload success: {effective_ur:.0f}%" + (f" (base {ur:.0f}% - {ep:.0f}% event)" if ep > 0 else ""))
        s.blit(Fonts.get(11).render(info_txt, True, TEXT_SECONDARY), (x, y))
        y += 18
        # Solar multipliers display:
        from constants import SOLAR_MULTIPLIERS
        sm_txt = f"Solar mult x{SOLAR_MULTIPLIERS [node.solar_level - 1]}"
        s.blit(Fonts.get(11).render(sm_txt, True, TEXT_SECONDARY), (x, y))

    def _draw_stats_card(self, s, rect, node):
        draw_rounded_rect(s, BG_CARD, rect, radius = CARD_RADIUS, border = 1, border_color = BORDER_COLOR)
        x, y = rect.x + CARD_PADDING, rect.y + CARD_PADDING
        s.blit(Fonts.get(13, bold = True).render("SESSION STATS", True, TEXT_MUTED), (x, y))
        y += 22

        rows = [
            ("Samples taken", str(node.total_samples)),
            ("Uploads OK", str(node.total_uploads_ok)),
            ("Uploads failed", str(node.total_uploads_fail)),
            ("Credits earned", f"{node.total_credits_earned:.2f}"),
            ("Sample interval", f"{node.sample_interval} min"),
            ("Upload interval", f"{node.upload_interval} min"),
            ("Storage full for", f"{node._storage_full_minutes / 60:.1f} hr"),
        ]
        for label, val in rows:
            l_s = Fonts.get(12).render(label, True, TEXT_SECONDARY)
            v_s = Fonts.get(12, bold = True).render(val, True, TEXT_PRIMARY)
            s.blit(l_s, (x, y))
            s.blit(v_s, (rect.right - CARD_PADDING - v_s.get_width(), y))
            y += 22

        # Win progress bar:
        y += 4
        pct = min(100, (node.day / WIN_DAY) * 100)
        s.blit(Fonts.get(11).render(f"Mission progress: Day {node.day} / {WIN_DAY}", True, TEXT_MUTED), (x, y))
        y += 16
        bar_rect = pygame.Rect(x, y, rect.width - CARD_PADDING * 2, 8)
        draw_rounded_rect(s, BAR_BG, bar_rect, radius = 4)
        fill_w = int(bar_rect.width * pct / 100)
        if fill_w > 0:
            draw_rounded_rect(s, ACCENT_BLUE, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, 8), radius = 4)

    def _draw_log_card(self, s, rect, node):
        draw_rounded_rect(s, BG_CARD, rect, radius = CARD_RADIUS, border = 1, border_color = BORDER_COLOR)
        x, y = rect.x + CARD_PADDING, rect.y + CARD_PADDING
        s.blit(Fonts.get(13, bold = True).render("EVENT LOG", True, TEXT_MUTED), (x, y))
        y += 20

        line_h = 16
        visible = max(1, (rect.bottom - y - CARD_PADDING) // line_h)
        log = node.log
        # Scroll: show from end:
        start = max(0, len(log) - visible - self.log_scroll)
        end = max(0, len(log) - self.log_scroll)
        visible_lines = log[start: end]

        for line in visible_lines:
            color = TEXT_SECONDARY
            if "[OK]" in line:
                color = ACCENT_GREEN
            elif "[FAIL]" in line or "[!]" in line:
                color = ACCENT_YELLOW
            elif "MAJOR" in line:
                color = ACCENT_RED
            elif "EVENT" in line or "Day" in line and "begins" in line:
                color = ACCENT_PURPLE
            elif "upgraded" in line or "renamed" in line:
                color = ACCENT_BLUE
            surf = Fonts.get(11).render(line, True, color)
            s.blit(surf, (x, y))
            y += line_h
            if y > rect.bottom - CARD_PADDING:
                break

    # Helper drawers:

    def _section_header(self, s, text, y, color):
        P = CARD_PADDING
        surf = Fonts.get(10, bold = True).render(text, True, color)
        s.blit(surf, (P + 8, y))
        pygame.draw.line(s, color, (P + 8+ surf.get_width() +6, y + 6), (SIDEBAR_WIDTH - P * 2, y +6), 1)
        return y + 18
    
    def _big_stat(self, s, value, subtitle, y, color):
        P = CARD_PADDING
        v_surf = Fonts.get(22, bold = True).render(value, True, color)
        s.blit(v_surf, (P + 10, y))
        sub_surf = Fonts.get(11).render(subtitle, True, TEXT_MUTED)
        s.blit(sub_surf, (P + 10 + v_surf.get_width() + 6, y + v_surf.get_height() - sub_surf.get_height() - 2))
        return y + v_surf.get_height() + 4
    
    def _progress_bar(self, s, pct, color, y):
        P = CARD_PADDING
        bar_rect = pygame.Rect(P + 8, y, SIDEBAR_WIDTH - P * 2 - 16, 6)
        draw_rounded_rect(s, BAR_BG, bar_rect, radius = 3)
        fill_w = int(bar_rect.width * _clamp(pct, 0, 100) / 100)
        if fill_w > 0:
            draw_rounded_rect(s, color, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, 6), radius = 3)
            return y + 12
        
    def _label_row(self, s, label, value, y):
        P = CARD_PADDING
        l_s = Fonts.get(11).render(label, True, TEXT_MUTED)
        v_s = Fonts.get(11).render(value, True, TEXT_SECONDARY)
        s.blit(l_s, (P + 10, y))
        s.blit(v_s, (SIDEBAR_WIDTH - P * 2 - v_s.get_width(), y))
        return y + 16
    
    # Popup event:

    def _draw_event_popup(self, s, node, evt):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        s.blit(overlay, (0, 0))

        pw, ph = 480, 280
        px = (self.W - pw) // 2
        py = (self.H - ph) // 2
        popup = pygame.Rect(px, py, pw, ph)
        draw_rounded_rect(s, BG_CARD, popup, radius = 12, border = 2, border_color = ACCENT_RED if evt.severity == "major" else ACCENT_YELLOW)

        x, y = px + 20, py + 18
        sev_col = ACCENT_RED if evt.severity == "major" else ACCENT_YELLOW
        sev_lbl = "MAJOR EVENT" if evt.severity == "major" else "EVENT"
        s.blit(Fonts.get(11, bold = True).render(sev_lbl, True, sev_col), (x, y))
        y += 20
        s.blit(Fonts.get(18, bold = True).render(evt.name, True, TEXT_PRIMARY), (x, y))
        y += 30

        # Wrap description:
        desc = evt.description
        words = desc.split()
        lines = []
        line = ""
        for w in words:
            test = (line + "" + w).strip()
            if Fonts.get(13).size(test)[0] > pw - 40:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        for ln in lines:
            s.blit(Fonts.get(13).render(ln, True, TEXT_SECONDARY), (x, y))
            y += 20

        y = py + ph - 70

        # Penalties:
        penalties = []
        if evt.solar_penalty:
            penalties.append(f"Solar - {evt.solar_penalty * 100:.0f}%")
        if evt.upload_penalty:
            penalties.append(f"Upload success - {evt.upload_penalty * 100:.0f}%")
        if hasattr(evt, "dq_drain") and evt.dq_drain:
            penalties.append(f"DQ drain + {evt.dq_drain:.2f}/min")
        if penalties:
            s.blit(Fonts.get(12).render("Penalties: " + " | ".join(penalties), True, ACCENT_ORANGE), (x, y))
        y += 20

        # Buttons:
        fix_lbl = f"Fix({evt.fix_cost} credits)"
        has_credits = node.credits >= evt.fix_cost

        fix_r = pygame.Rect(px + 20, py + ph - 44, 180, 32)
        ign_r = pygame.Rect(px + pw - 200, py + ph - 44, 180, 32)

        fix_col = ACCENT_GREEN if has_credits else (50, 50, 50)
        draw_rounded_rect(s, fix_col, fix_r, radius = 7)
        fs = Fonts.get(13, bold = True).render(fix_lbl, True, TEXT_WHITE)
        s.blit(fs, fs.get_rect(center = fix_r.center))
        self._btn("evt_fix", fix_r)

        draw_rounded_rect(s, BG_PANEL, ign_r, radius = 7, border = 1, border_color = BORDER_BRIGHT)
        ig = Fonts.get(13, bol = True).render("Ignore (keep penalty)", True, TEXT_SECONDARY)
        s.blit(ig, ig.get_rect(center = ign_r.center))
        self._btn("evt_ignore", ign_r)

    # Settings popup:

    def _draw_settings_panel(self, s, node = None):
        pw, ph = 420, 240
        px = (self.W - pw) // 2
        py = (self.H - ph) // 2
        popup = pygame.Rect(px, py, pw, ph)

        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        s.blit(overlay, (0, 0))

        draw_rounded_rect(s, BG_CARD, popup, radius = 12, border = 1, border_color = BORDER_BRIGHT)

        x, y = px + 20, py + 18
        s.blit(Fonts.get(15, bold = True).render("[SET] Settings", True, TEXT_PRIMARY), (x, y))
        y += 34

        def input_row(label, buf_key, cur_val):
            nonlocal y
            s.blit(Fonts.get(13).render(label, True, TEXT_SECONDARY), (x, y))
            inp_r = pygame.Rect(px + pw - 120 - 20, y- 3, 120, 26)
            active = (self.active_input == buf_key)
            draw_rounded_rect(s, BG_DARK if active else BG_PANEL, inp_r, radius = 5, border = 1, border_color = ACCENT_BLUE if active else BORDER_COLOR)
            val = getattr(self, buf_key + "_input_text") if active \
                  else str(cur_val)
            ts = Fonts.get(13).render(val + ("|" if active else ""), True, TEXT_WHITE if active else TEXT_PRIMARY)
            s.blit(ts, ts.get_rect(midleft = (inp_r.x + 8, inp_r.centery)))
            self._btn("input_" + buf_key, inp_r)
            y += 36

        if hasattr(self, "_node"):
            nd = self._node 
            input_row("Sample interval (min)", "sample", nd.sample_interval)
            input_row("Upload interval (min)", "upload", nd.upload_interval)

        # Apply / Close:
        apply_r = pygame.Rect(px + 20, py + ph - 44, 140, 32)
        close_r = pygame.Rect(px + pw - 160, py + ph - 44, 140, 32)
        draw_rounded_rect(s, ACCENT_BLUE, apply_r, radius = 7)
        s.blit(Fonts.get(13, bold = True).render("Apply", True, TEXT_WHITE), Fonts.get(13, bold = True).render("Apply", True, TEXT_WHITE).get_rect(center = apply_r.center))
        self._btn("settings_apply", apply_r)

        draw_rounded_rect(s, BG_PANEL, close_r, radius = 7, border = 1, border_color = BORDER_COLOR)
        s.blit(Fonts.get(13, bold = True).render("Close", True, TEXT_SECONDARY), Fonts.get(13, bold = True).render("Close", True, TEXT_SECONDARY).get_rect(center = close_r.center))
        self._btn("settings_close", close_r)

    # Rename popup:

    def _draw_rename_box(self, s):
        pw, ph = 380, 140
        px = (self.W - pw) // 2
        py = (self.H - ph) // 2
        popup = pygame.Rect(px, py, pw, ph)

        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        s.blit(overlay, (0, 0))

        draw_rounded_rect(s, BG_CARD, popup, radius = 12, border = 1, border_color = BORDER_BRIGHT)
        x, y = px + 20, py + 20
        s.blit(Fonts.get(14, bold = True).render("Rename Node", True, TEXT_PRIMARY), (x, y))
        y += 32

        inp_r = pygame.Rect(px + 20, y, pw - 40, 30)
        draw_rounded_rect(s, BG_DARK, inp_r, radius = 5, border = 1, border_color = ACCENT_BLUE)
        ts = Fonts.get(14).render(self.rename_text + "|", True, TEXT_WHITE)
        s.blit(ts, ts.get_rect(midleft = (inp_r.x + 8, inp_r.centery)))
        y += 44

        ok_r = pygame.Rect(px + 20, y, 120, 30)
        cn_r = pygame.Rect(px + pw - 140, y, 120, 30)
        draw_rounded_rect(s, ACCENT_BLUE, ok_r, radius = 6)
        s.blit(Fonts.get(13, bold = True).render("Rename", True, TEXT_WHITE), Fonts.get(12, bold = True).render("Rename", True, TEXT_WHITE).get_rect(center = ok_r.center))
        self._btn("rename_ok", ok_r)

        draw_rounded_rect(s, BG_PANEL, cn_r, radius = 6, border = 1, border_color = BORDER_COLOR)
        s.blit(Fonts.get(13, bold = True).render("Cancel", True, TEXT_SECONDARY), Fonts.get(13, bold = True).render("Cancel", True, TEXT_SECONDARY).get_rect(center = cn_r.center))
        self._btn("rename_cancel", cn_r)
        
    # Game over screen:

    def _draw_game_over(self, node):
        s = self.screen
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        s.blit(overlay, (0, 0))

        cx, cy = self.W // 2, self.H // 2
        if node.game_won:
            title_col = ACCENT_GREEN
            title_txt = "MISSION COMPLETE"
            sub_txt = f"Node survived 365 days! Final credits: {node.credits:.2f}"
        else:
            title_col = ACCENT_RED
            title_txt = "NODE OFFLINE"
            sub_txt = node.lose_reason

        t_surf = Fonts.get(42, bold = True).render(title_txt, True, title_col)
        s.blit(t_surf, t_surf.get_rect(center = (cx, cy - 50)))
        sub_s = Fonts.get(18).render(sub_txt, True, TEXT_SECONDARY)
        s.blit(sub_s, sub_s.get_rect(center = (cx, cy + 20)))

        restart_r = pygame.Rect(cx - 90, cy + 70, 180, 40)
        draw_rounded_rect(s, ACCENT_BLUE, restart_r, radius = 8)
        rs = Fonts.get(15, bold = True).render("Play Again", True, TEXT_WHITE)
        s.blit(rs, rs.get_rect(center = restart_r.center))
        self._btn("restart", restart_r)

    # Feedback Flash:

    def _draw_feedback(self):
        alpha = min(225, self._feedback_timer * 5)
        surf = Fonts.get(14, bold = True).render(self._feedback_msg, True, self._feedback_color)
        x = self.W // 2 - surf.get_width() // 2
        y = TOPBAR_HEIGHT + 12
        self.screen.blit(surf, (x, y))

    def flash(self, msg: str, color = None):
        self._feedback_msg = msg
        self._feedback_timer = 90
        self._feedback_color = color or ACCENT_GREEN

    # Input handling:

    def handle_event(self, event, node) -> str | None:
        self._node = node 

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event, node)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.log_scroll = min(self.log_scroll + 2, max(0, len(node.log) - 5))
            elif event.button == 5:
                self.log_scroll = max(0, self.log_scroll - 2)
            elif event.button == 1:
                return self._handle_click(event.pos, node)
            
        return None
    
    def _handle_keydown(self, event, node):
        if self.active_input == "rename":
            if event.key == pygame.K_RETURN:
                node.rename(self.rename_text)
                self.rename_text = ""
                self.show_rename_box = False
                self.active_input = None
            elif event.key == pygame.K_BACKSPACE:
                self.rename_text = self.rename_text[:-1]
            else:
                if len(self.rename_text) < 24:
                    self.rename_text += event.unicode
            return None
        
        if self.active_input in ("sample", "upload"):
            buf = self.active_input + "_input_text"
            cur = getattr(self, buf)
            if event.key == pygame.K_RETURN:
                self._apply_settings(node)
            elif event.key == pygame.K_ESCAPE:
                self.active_input = None
            elif event.key == pygame.K_BACKSPACE:
                setattr(self, buf, cur[:-1])
            elif event.unicode.isdigit():
                setattr(self, buf, cur + event.unicode)
            return None
        
        return None
    
    def _handle_click(self, pos, node):
        for key, rect in self._btn_rects.items():
            if rect.collidepoint(pos):
                return self._dispatch(key, node)
        return None
    
    def _dispatch(self, key, node):
        if key == "rename":
            self.rename_text = node.name
            self.show_rename_box = True
            self.active_input = "rename"

        elif key == "rename_ok":
            node.rename(self.rename_text)
            self.rename_text = ""
            self.show_rename_box = False 
            self.active_input = None

        elif key == "rename_cancel":
            self.show_rename_box = False
            self.active_input = None
            self.rename_text = ""

        elif key  == "sleep_toggle":
            node.toggle_sleep()

        elif key == "settings":
            self.show_settings_panel = not self.show_settings_panel
            if self.show_settings_panel:
                self.sample_input_text = str(node.sample_interval)
                self.upload_input_text = str(node.upload_interval)

        elif key == "settings_apply":
            self._apply_settings(node)

        elif key == "settings_close":
            self.show_settings_panel = False
            self.active_input = None

        elif key.startswith("input_"):
            field = key[len("input_"):]
            self.active_input = field

        elif key.startswith("speed_"):
            return "speed:" + key.split("_")[1]
        
        elif key == "upg_battery":
            msg = node.upgrade_battery()
            self.flash(msg, ACCENT_GREEN if "upgraded" in msg else ACCENT_RED)

        elif key == "upg_solar":
            msg = node.upgrade_solar()
            self.flash(msg, ACCENT_GREEN if "upgraded" in msg else ACCENT_RED)

        elif key == "upg_antenna":
            msg = node.upgrade_antenna()
            self.flash(msg, ACCENT_GREEN if "upgraded" in msg else ACCENT_RED)

        elif key == "evt_fix":
            evt = node.events.pending_popup
            if evt:
                msg = node.fix_event(evt.id)
                node.events.pending_popup = None
                self.flash(msg, ACCENT_GREEN if "Fixed" in msg else ACCENT_RED)

        elif key == "evt_ignore":
            if node.events.pending_popup:
                node.events.pending_popup.acknowledged = True
                node.events.pending_popup = None

        elif key == "event_panel":
            if node.events.active_events:
                node.events.pending_popup = node.events.active_events[0]

        elif key == "quit":
            pygame.quit()
            import sys
            sys.exit()

        elif key == "restart":
            return "restart"
        
        return None
    
    def _apply_settings(self, node):
        try:
            s = int(self.sample_input_text)
            u = int(self.upload_input_text)
            if s > 0:
                node.set_sample_interval(s)
            if u > 0:
                node.set_upload_interval(u)
            self.flash("Settings applied.", ACCENT_GREEN)
        except ValueError:
            self.flash("Invalid value - enter whole numbers.", ACCENT_RED)
            self.active_input = None
            self.show_settings_panel = False

    def draw(self, node, speed_index: int):
        self._node = node
        self._btn_rects = {}

        s = self.screen
        s.fill(BG_DARK)

        self._draw_topbar(node, speed_index)
        self._draw_sidebar(node)
        self._draw_main(node)

        # Popups priority:
        if node.events.pending_popup and not node.events.pending_popup.acknowledged:
            self._draw_event_popup(s, node, node.events.pending_popup)
        elif self.show_rename_box:
            self._draw_rename_box(s)
        elif self.show_settings_panel:
            self._draw_settings_panel(s)

        if node.game_over:
            self._draw_game_over(node)

        if self._feedback_timer > 0:
            self._draw_feedback()
            self._feedback_timer -= 1

        pygame.display.flip()