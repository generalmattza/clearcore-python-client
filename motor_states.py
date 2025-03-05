import asyncio
from enum import Enum
from app_monitor import TextElement
from app_monitor.text_formatter import TextFormat

class MotorReadyState(Enum):
    MOTOR_DISABLED = 0
    MOTOR_ENABLING = 1
    MOTOR_FAULTED = 2
    MOTOR_READY = 3
    MOTOR_MOVING = 4

    def __str__(self):
        descriptions = {
            MotorReadyState.MOTOR_DISABLED: "DISABLED",
            MotorReadyState.MOTOR_ENABLING: "ENABLING",
            MotorReadyState.MOTOR_FAULTED: "FAULTED",
            MotorReadyState.MOTOR_READY: "READY",
            MotorReadyState.MOTOR_MOVING: "MOVING",
        }
        return descriptions[self]


class MotorAlertRegisterReader:

    # Reverse mapping for easier lookup
    _alert_map = {
        0: "MotionCanceledInAlert",
        1: "MotionCanceledPositiveLimit",
        2: "MotionCanceledNegativeLimit",
        3: "MotionCanceledSensorEStop",
        4: "MotionCanceledMotorDisabled",
        5: "MotorFaulted",
    }

    _alert_descriptions_map = {
        "MotionCanceledInAlert": "ALERT",
        "MotionCanceledPositiveLimit": "POS-LIMIT",
        "MotionCanceledNegativeLimit": "NEG-LIMIT",
        "MotionCanceledSensorEStop": "E-STOP",
        "MotionCanceledMotorDisabled": "DISABLED",
        "MotorFaulted": "FAULT",
    }

    def __init__(self, alert_index=None):
        # Store the binary alert string
        self.alert_index = int(alert_index) if alert_index else 0

    def get_active_alerts(self, alert_index=None):
        # Generate a list of active alerts
        if alert_index is not None:
            self.alert_index = alert_index
        active_alerts = [
            self._alert_map[i]
            for i in range(len(self._alert_map))
            if (self.alert_index >> i) & 1
        ]
        return active_alerts

    def get_alert_descriptions(self, alert_index=None):
        if alert_index is not None:
            self.alert_index = alert_index
        active_alerts = self.get_active_alerts()
        return [self._alert_descriptions_map[alert] for alert in active_alerts]

    @property
    def total_alerts(self):
        return len(self.get_active_alerts())


class MotorStatusElement(TextElement):

    def update(self, text):
        state = MotorReadyState(int(text))
        return super().update(state)

    def display(self):
        """Render the text element for display."""
        self.text_format = TextFormat(ansi_enabled=True)
        if self.text == "DISABLED":
            self.text_format.fg_color = "red"
        elif self.text == "FAULTED":
            self.text_format.fg_color = "yellow"
        else:
            self.text_format.fg_color = "green"
        text = self.text_format.format_text(str(self.text))
        full_text = (self.static_text or "") + text
        return (
            full_text
        )

class MotorAlertElement(TextElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_index = 0  # Tracks the current alert index
        self.current_alert = ""  # Stores the latest alert
        self.current_code = 0  # Stores the current alert code
        self.cycling_task = None  # Track the cycling task
        self.start_cycling()

    async def cycle_alerts(self):
        """Continuously cycle through the alerts present in the alert register."""
        while True:
            if self.current_code == 0:  # If no alerts, stop cycling
                self.current_alert = ""
                return
            
            alert_reader = MotorAlertRegisterReader()
            alerts = alert_reader.get_alert_descriptions(alert_index=self.current_code)

            if alerts:
                self.current_alert = alerts[self.current_index]

                # Move to the next alert index (cycle back to 0 if at the end)
                self.current_index = (self.current_index + 1) % alert_reader.total_alerts
            else:
                self.current_alert = ""  # Clear alert if no active alerts

            await asyncio.sleep(3)  # Cycle every 3 seconds

    def start_cycling(self):
        """Start the alert cycling task only if it's not already running."""
        if not self.cycling_task or self.cycling_task.done():
            self.cycling_task = asyncio.create_task(self.cycle_alerts())

    def stop_cycling(self):
        """Cancel the cycling task if running."""
        if self.cycling_task and not self.cycling_task.done():
            self.cycling_task.cancel()

    def update(self, idx):
        """Update the alert index and handle clearing."""
        if idx == 0:  # If alerts are cleared, reset everything
            self.current_code = 0
            self.current_alert = ""
            self.stop_cycling()
        else:
            self.current_code = idx
            self.start_cycling()

        return super().update(self.current_alert)
    


from app_monitor.elements_base import RangeBar

class ColoredRangeBar(RangeBar):

    def display(self):
        """Render the range bar for display."""
        progress_ratio = (self.current_value - self.min_value) / (
            self.max_value - self.min_value
        )
        numeric_value = (
            f"{self.current_value:>{self.max_display_length}.{self.digits}f}"
        )
        full_display_value = f"{numeric_value} {self.unit}".ljust(
            self.max_display_length + len(self.unit)
        )
        display_value = (
            self.text_format.format_text(full_display_value)
            if self.text_format
            else full_display_value
        )
        bar_width = self.width - self.max_label_length - self.max_display_length - 13
        marker_position = min(int(bar_width * progress_ratio), bar_width - 1)
        bar = (
            self.range_trace * marker_position
            + self.marker_trace
            + self.range_trace * (bar_width - marker_position - 1)
        )
        self.bar_format = TextFormat(ansi_enabled=True)
        if abs(progress_ratio) > 0.6:
            self.bar_format.fg_color = "yellow"
        if abs(progress_ratio) >= 0.8:
            self.bar_format.fg_color = "red"
        formatted_bar = self.bar_format.format_text(bar) if self.bar_format else bar
        padded_label = self.label.ljust(self.max_label_length)
        return f"{padded_label} [{formatted_bar}] {display_value}"
