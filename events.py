import random
from constants import (
    MINOR_EVENTS, MAJOR_EVENTS, MINOR_EVENT_CHANCE_WEEKLY, MAJOR_EVENT_CHANCE_MONTHLY,
)

class ActiveEvent:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.severity = data["severity"]
        self.fix_cost = data["fix_cost"]
        self.solar_penalty = data.get("solar_penalty", 0.0)
        self.upload_penalty = data.get("upload_penalty", 0.0)
        self.dq_drain = data.get("dq_drain", 0.0)
        self.capacity_penalty = data.get("capacity_penalty", 0.0)
        self.acknowledged = False

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "fix_cost": self.fix_cost,
            "solar_penalty": self.solar_penalty,
            "dq_drain": self.dq_drain,
            "capacity_penalty": self.capacity_penalty,
        }
    
class EventSystem:
    def __init__(self):
        self.active_events: list[ActiveEvent] = []
        self.pending_popup: ActiveEvent | None = None 
        self._minutes_since_last_week_check = 0.0
        self._minutes_since_last_month_check = 0.0
        self.WEEK_MINUTES = 7 * 24 * 60
        self.MONTH_MINUTES = 30 * 24 * 60

    def update(self, delta_minutes: float) -> list[str]:
        messages = []
        self._minutes_since_last_week_check += delta_minutes
        self._minutes_since_last_month_check += delta_minutes

        if self._minutes_since_last_week_check >= self.WEEK_MINUTES:
            self._minutes_since_last_week_check -= self.WEEK_MINUTES
            msg = self._try_weekly_event()
            if msg:
                messages.append(msg)
            
        if self._minutes_since_last_month_check >= self.MONTH_MINUTES:
            self._minutes_since_last_month_check -= self.MONTH_MINUTES
            msg = self._try_monthly_event()
            if msg:
                messages.append(msg)

        return messages 
    
    def _try_weekly_event(self) -> str | None:
        if random.random() < MINOR_EVENT_CHANCE_WEEKLY:
            event_data = random.choice(MINOR_EVENTS)
            return self._add_event(event_data)
        return None
    
    def _try_monthly_event(self) -> str | None:
        if random.random() < MAJOR_EVENT_CHANCE_MONTHLY:
            event_data = random.choice(MAJOR_EVENTS)
            return self._add_event(event_data)
        return None
    
    def _add_event(self, event_data: dict) -> str:
        for existing in self.active_events:
            if existing.id == event_data["id"]:
                return None
        evt = ActiveEvent(event_data)
        self.active_events.append(evt)
        if self.pending_popup is None:
            self.pending_popup = evt
        label = "⚠ MAJOR" if evt.severity == "major" else "ℹ EVENT"
        return f"{label}: {evt.name} - {evt.description}"
    
    def fix_event(self, event_id: str, credits: float) -> tuple[bool, float, str]:
        for evt in self.active_events:
            if evt.id == event_id:
                if credits >= evt.fix_cost:
                    self.active_events.remove(evt)
                    return True, evt.fix_cost, f"✓ Fixed: {evt.name}"
                else:
                    return False, 0, f"✗ Not enough credits to fix {evt.name}"
        return False, 0, "Event not found."
    
    def dismiss_popup(self):
        self.pending_popup = None
        for evt in self.active_events:
            if not evt.acknowledged:
                evt.acknowledged = True
                self.pending_popup = evt
                break

    def total_solar_penalty(self) -> float:
        total = sum(e.solar_penalty for e in self.active_events)
        return min(total, 1.0)
    
    def total_upload_penalty(self) -> float:
        total = sum(e.upload_penalty for e in self.active_events)
        return min(total, 1.0)
    
    def total_dq_drain(self) -> float:
        return sum(e.dq_drain for e in self.active_events)
    
    def total_capacity_penalty(self) -> float:
        total = sum(e.capacity_penalty for e in self.active_events)
        return min(total, 0.5)