import random
from constants import (
    BATTERY_CAPACITIES, BATTERY_START_UNITS, STORAGE_CAPACITY_MB, DATA_QUALITY_START, CREDITS_START, AWAKE_DRAIN_PER_MINUTE, SLEEP_DRAIN_PER_MINUTE, SAMPLE_ENERGY_COST, SAMPLE_DATA_MB, UPLOAD_BASE_COST, UPLOAD_PER_MB_COST, ANTENNA_UPLOAD_SUCCESS, ANTENNA_COST_MULTIPLIER, SOLAR_MULTIPLIERS, UPGRADE_COSTS, DQ_SAMPLE_BONUS, DQ_UPLOAD_SUCCESS_BONUS, DQ_UPLOAD_FAIL_PENALTY, DQ_IDLE_PENALTY_PER_MIN, DQ_STORAGE_FULL_PENALTY, DQ_MIN, DQ_MAX, UPLOAD_REWARD_DIVISOR, DEFAULT_SAMPLE_INTERVAL_MIN, DEFAULT_UPLOAD_INTERVAL_MIN, DEFAULT_SLEEP_DURATION_MIN, DEFAULT_NODE_NAME, LOSE_BATTERY, LOSE_DQ, LOSE_STORAGE_FULL_DAYS, WIN_DAY,
)
from weather import WeatherSystem
from events import EventSystem

class Node:
    def __init__(self):
        self.name = DEFAULT_NODE_NAME 
        
        # Levels:
        self.battery_level = 1
        self.solar_level = 1
        self.antenna_level = 1

        # Battery:
        self.battery_max = BATTERY_CAPACITIES[self.battery_level - 1]
        self.battery_units = float(BATTERY_START_UNITS)

        # Storage:
        self.storage_max = STORAGE_CAPACITY_MB 
        self.storage_used = 0.0

        # Data quality & credits:
        self.data_quality = float(DATA_QUALITY_START)
        self.credits = float(CREDITS_START)

        # Player-controlled Settings:
        self.sample_interval = DEFAULT_SAMPLE_INTERVAL_MIN
        self.upload_interval = DEFAULT_UPLOAD_INTERVAL_MIN
        self.sleep_duration = DEFAULT_SLEEP_DURATION_MIN 

        # Internal timers:
        self._sample_timer = 0.0
        self._upload_timer = 0.0

        # State:
        self.sleeping = False
        self.status_text = "ONLINE"
        
        # Storage-full tracking:
        self._storage_full_minutes = 0.0

        #Statistics:
        self.total_uploads_ok = 0
        self.total_uploads_fail = 0
        self.total_samples = 0
        self.total_credits_earned = 0.0

        #Subsystems:
        self.weather = WeatherSystem()
        self.events = EventSystem()

        # Game clock:
        self.game_time_minutes = 6 * 60   # Start at 6:00 
        self.day = 1

        # Win/lose:
        self.game_over = False
        self.game_won = False
        self.lose_reason = ""

        #Log:
        self.log: list[str] = []
        self._log("Node online. Welcome, operator.")

    # Main update loop:

    def update(self, delta_real_seconds: float, speed_multiplier: float):
        if self.game_over:
            return 
        
        delta_minutes = delta_real_seconds * speed_multiplier

        # Game clock:
        prev_day = self.day
        self.game_time_minutes += delta_minutes 
        self.day = int(self.game_time_minutes // (24 * 60)) + 1

        if self.day != prev_day:
            self._log(f"Day {self.day} begins.")

        # Subsystems:
        current_hour = (self.game_time_minutes % (24 * 60)) / 60
        self.weather.update(delta_minutes, current_hour, self.day)
        if self.weather.current == "Rainy" or self.weather.current == "Storm":
            for evt in self.events.active_events[:]:
                if evt.id in ("light_dust", "heavy_dust"):
                    self.events.active_events.remove(evt)
                    self._log(f"[INFO] Rain washed away: {evt.name}")
        event_msgs = self.events.update(delta_minutes)
        for m in event_msgs:
            self._log(m)

        # Power drain:
        drain_rate = SLEEP_DRAIN_PER_MINUTE if self.sleeping else AWAKE_DRAIN_PER_MINUTE 
        self._drain_battery(drain_rate * delta_minutes)

        # Solar charging:
        if self._is_daytime():
            self._do_solar(delta_minutes)

        # Sampling:
        if not self.sleeping:
            self._sample_timer += delta_minutes
            if self._sample_timer >= self.sample_interval:
                self._sample_timer -= self.sample_interval
                self._do_sample()

        # Uploading:
        self._upload_timer += delta_minutes 
        if self._upload_timer >= self.upload_interval:
            self._upload_timer -= self.upload_interval
            self._do_upload()

        # Data quality passives:
        self._update_data_quality(delta_minutes)

        # Storage full penalty:
        if self.storage_used >= self.storage_max:
            self._storage_full_minutes += delta_minutes
            self.data_quality -= DQ_STORAGE_FULL_PENALTY * delta_minutes 
        else: 
            self._storage_full_minutes = 0.0

        self.data_quality = max(DQ_MIN, min(DQ_MAX, self.data_quality))

        # Status text:
        self.status_text = "SLEEPING" if self.sleeping else "ONLINE"

        # Check lose/win conditions:
        self._check_conditions()

    # Internal mechanics:

    def _is_daytime(self) -> bool:
        hour = (self.game_time_minutes % (24 * 60)) / 60
        from constants import DAYTIME_START, DAYTIME_END
        return DAYTIME_START <= hour < DAYTIME_END
    
    def _drain_battery(self, units: float):
        self.battery_units = max(0.0, self.battery_units - units)

    def _effective_max_battery(self) -> float:
        base = BATTERY_CAPACITIES[self.battery_level - 1]
        penalty = self.events.total_capacity_penalty()
        return base * (1.0 - penalty)
    
    def _do_solar(self, delta_minutes: float):
        base_per_hour = self.weather.get_solar_base()
        solar_mult = SOLAR_MULTIPLIERS[self.solar_level - 1]
        event_penalty = self.events.total_solar_penalty()
        effective_per_hour = base_per_hour * solar_mult * (1.0 - event_penalty)
        charge = effective_per_hour * (delta_minutes / 60.0)
        max_bat = self._effective_max_battery()
        self.battery_units = min(max_bat, self.battery_units + charge)

    def _do_sample(self):
        if self.storage_used >= self.storage_max:
            self._log("[!] Storage full - sampling skipped.")
            return
        if self.battery_units <= SAMPLE_ENERGY_COST:
            self._log("[!] Low battery - sampling skipped.")
            return
        
        self._drain_battery(SAMPLE_ENERGY_COST)
        self.storage_used = min(self.storage_max, self.storage_used + SAMPLE_DATA_MB)
        self.data_quality = min(DQ_MAX, self.data_quality + DQ_SAMPLE_BONUS)
        self.total_samples += 1

    def _do_upload(self):
        if self.storage_used <= 0:
            return 
        
        mb_to_upload = self.storage_used 
        base_success = ANTENNA_UPLOAD_SUCCESS[self.antenna_level - 1]
        event_penalty = self.events.total_upload_penalty()
        success_rate = max(0.0, base_success - event_penalty)
        cost_mult = ANTENNA_COST_MULTIPLIER[self.antenna_level - 1]
        energy_cost = (UPLOAD_BASE_COST + UPLOAD_PER_MB_COST * mb_to_upload) * cost_mult
        
        if self.battery_units < energy_cost:
            self._log("[!] Not enough battery for upload.")
            return
        
        self._drain_battery(energy_cost)

        if random.random() <= success_rate:
            # Success:
            reward = (mb_to_upload * self.data_quality) / UPLOAD_REWARD_DIVISOR
            self.credits += reward 
            self.total_credits_earned += reward
            self.data_quality = min(DQ_MAX, self.data_quality + DQ_UPLOAD_SUCCESS_BONUS)
            self.storage_used = 0.0
            self.total_uploads_ok += 1
            self._log(f"[OK] Upload OK - {mb_to_upload:.0f} MB | + {reward:.2f} credits")
        else:
            #Failure:
            self.data_quality = max(DQ_MIN, self.data_quality - DQ_UPLOAD_FAIL_PENALTY)
            self.storage_used = 0.0
            self.total_uploads_fail += 1
            self._log(f"[FAIL] Upload failed - {mb_to_upload:.0f} MB lost. DQ - {DQ_UPLOAD_FAIL_PENALTY}")
        
    def _update_data_quality(self, delta_minutes: float):
        if self.sample_interval > 30:
            extra = (self.sample_interval - 30) / 30.0
            self.data_quality -= DQ_IDLE_PENALTY_PER_MIN * extra * delta_minutes 

        # Event drift:
        extra_drain = self.events.total_dq_drain()
        if extra_drain > 0:
            self.data_quality -= extra_drain * delta_minutes 

    def _check_conditions(self):
        # Battery dead:
        if self.battery_units <= LOSE_BATTERY:
            self.game_over = True
            self.lose_reason = "Battery depleted - node offline."
            return
        
        # DQ too low:
        if self.data_quality <= LOSE_DQ:
            self.game_over = True
            self.lose_reason = "Data Quality critically low - mission failed."
            return
        
        # Storage full two long (7 days):
        if self._storage_full_minutes >= LOSE_STORAGE_FULL_DAYS * 24 * 60:
            self.game_over = True
            self.lose_reason = "Storage full for 7 days - data integrity lost."
            return
        
        # Win condition:
        if self.day > WIN_DAY:
            self.game_over = True
            self.game_won = True

    # Public accessors:

    def battery_percent(self) -> float:
        max_bat = self._effective_max_battery()
        if max_bat <= 0:
            return 0.0
        return max(0.0, min(100.0, (self.battery_units / max_bat) * 100.0))
    
    def storage_percent(self) -> float:
        return max(0.0, min(100.0, (self.storage_used / self.storage_max) * 100.0))
    
    def solar_input_now(self) -> float:
        if not self._is_daytime():
            return 0.0
        base = self.weather.get_solar_base()
        mult = SOLAR_MULTIPLIERS[self.solar_level - 1]
        penalty = self.events.total_solar_penalty()
        return base * mult * (1.0 - penalty)
    
    def time_string(self) -> str:
        total_min = int(self.game_time_minutes) % (24 * 60)
        h = total_min // 60
        m = total_min % 60
        return f"{h:02d}:{m:02d}"
    
    # Player actions:

    def set_sample_interval(self, minutes: int):
        self.sample_interval = max(1, minutes)
        self._log(f"Sample interval set to {self.sample_interval} min.")

    def set_upload_interval(self, minutes: int):
        self.upload_interval = max(1, minutes)
        self._log(f"Upload interval set to {self.upload_interval} min.")

    def toggle_sleep(self):
        self.sleeping = not self.sleeping
        state = "SLEEPING" if self.sleeping else "AWAKE"
        self._log(f"Node set to {state}.")

    def rename(self, new_name: str):
        if new_name.strip():
            self.name = new_name.strip()
            self._log(f"Node renamed to '{self.name}'.")

    def upgrade_battery(self) -> str:
        if self.battery_level >= 4:
            return "Battery already at max level."
        cost = UPGRADE_COSTS["battery"][self.battery_level]
        if self.credits < cost:
            return f"Need {cost} credits (have {self.credits:.1f})."
        self.credits -= cost 
        self.battery_level += 1
        new_cap = BATTERY_CAPACITIES[self.battery_level - 1]
        self.battery_max = new_cap
        self.battery_units = float(new_cap)
        msg = f"Battery upgraded to L{self.battery_level} ({new_cap} units max). Fully recharged."
        self._log("[BAT]" + msg)
        for evt in self.events.active_events[:]:
            if evt.id == "battery_damage":
                self.events.active_events.remove(evt)
                self._log(f"[INFO] Upgrade cleared event: {evt.name}")
        return msg
    
    def upgrade_solar(self) -> str:
        if self.solar_level >= 4:
            return "Solar panel already at max level."
        cost = UPGRADE_COSTS["solar"][self.solar_level]
        if self.credits < cost:
            return f"Need {cost} credits (have {self.credits:.1f})."
        self.credits -= cost
        self.solar_level += 1
        msg = f"Solar panel upgraded to L{self.solar_level} (x{SOLAR_MULTIPLIERS[self.solar_level - 1]})."
        self._log("[SOL]" + msg)
        for evt in self.events.active_events[:]:
            if evt.id in ("light_dust", "heavy_dust", "solar_damage"):
                self.events.active_events.remove(evt)
                self._log(f"[INFO] Upgrade cleared event: {evt.name}")
        return msg
    
    def upgrade_antenna(self) -> str:
        if self.antenna_level >= 4:
            return "Antenna already at max level."
        cost = UPGRADE_COSTS["antenna"][self.antenna_level]
        if self.credits < cost:
            return f"Need {cost} credits (have {self.credits:.1f})."
        self.credits -= cost 
        self.antenna_level += 1
        rate = ANTENNA_UPLOAD_SUCCESS[self.antenna_level - 1] * 100
        msg = f"Antenna upgraded to L{self.antenna_level} ({rate:.0f}% upload success)."
        self._log("[ANT]" + msg)
        for evt in self.events.active_events[:]:
            if evt.id in ("bird_nest", "wifi_minor", "wifi_major"):
                self.events.active_events.remove(evt)
                self._log(f"[INFO] Upgrade cleared event: {evt.name}")
        return msg 
    
    def fix_event(self, event_id: str) -> str:
        success, cost, msg = self.events.fix_event(event_id, self.credits)
        if success:
            self.credits -= cost
        self._log(msg)
        return msg
    
    def _log(self, msg: str):
        from constants import LOG_MAX_LINES 
        ts = self.time_string()
        entry = f"[Day {self.day} {ts}] {msg}"
        self.log.append(entry)
        if len(self.log) > LOG_MAX_LINES:
            self.log.pop(0)