#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-01-01
# version ='0.0.1'
# ---------------------------------------------------------------------------
"""a_short_project_description"""
# ---------------------------------------------------------------------------

from logging.config import dictConfig
import asyncio

# Import the load_configs function
from config_loader import load_configs
from app_monitor.text_formatter import TextFormat

from app_monitor import (
    TerminalManager,
    RangeBar,
    SerialUpdateServer,
)
from motor_states import MotorStatusElement, MotorAlertElement
from app_monitor.server import StructDecoder, WindowValidator
from threadsafe_serial import ThreadSafeSerial


LOGGING_CONFIG_FILEPATH = "config/logger.yaml"
# APP_CONFIG_FILEPATH = "config/application.toml"

# # Load user configurations using the config_loader module
logging_config = load_configs(LOGGING_CONFIG_FILEPATH)

# # Configure logging using the specified logging configuration
dictConfig(logging_config)


def create_serial_thread():
    threadsafe_serial = ThreadSafeSerial(
        port="COM6",
        baudrate=115200,
        timeout=3,
    )
    return threadsafe_serial

async def main():
    # logging.info(configs["application"])

    # Create a MonitorManager instances
    manager = TerminalManager()

    # Add a progress bar and table elements with formatting
    BAR_WIDTH = 30
    text_format = TextFormat(bold=True)


    # Example instantiation of the RangeBar
    axis_properties = dict(
        # width=50,  # Total width of the bar (e.g., 50 characters)
        # bar_format={"fg_color": "green"},  # Custom formatting for the bar (optional)
        text_format=text_format,  # Custom formatting for the display text (optional)
        max_label_length=12,  # Maximum length of the label (e.g., 5 characters)
        max_display_length=5,  # Maximum length of the value (e.g., 5 characters)
        marker_trace="█",
        range_trace="-",
        digits=1,
        # scale=60 / 6000,
    )

    position = RangeBar(
        element_id="position", label="Axis Position", unit="mm", min_value=0,
        max_value=1000, **axis_properties
    )
    axis_velocity = RangeBar(
        element_id="velocity", label="Axis Vel", unit="mm/s", min_value=-100,
        max_value=100, **axis_properties
    )
    motor_speed = RangeBar(
        element_id="motor_speed", label="Motor Speed", unit="rpm", min_value=-1500,
        max_value=1500, **axis_properties
    )
    axis_torque_current = RangeBar(
        element_id="torque_current", label="Torque", unit="%", min_value=-100,
        max_value=100, **axis_properties
    )
    axis_torque_limit = RangeBar(
        element_id="torque_limit", label="Torque Limit", unit="%", min_value=0,
        max_value=100, **axis_properties
    )
    motor_status = MotorStatusElement(element_id="status", static_text="Motor Status: ")
    motor_faults = MotorAlertElement(element_id="faults", static_text="Faults: ")

    # logger = LogMonitor(
    #     element_id="logger",
    #     timestamp=True,
    #     timestamp_format="%H:%M:%S.%f",
    #     # timestamp_significant_digits=3,
    #     border=True,
    # )

    manager.add_element(position)
    manager.add_element(axis_velocity)
    manager.add_element(motor_speed)
    manager.add_element(axis_torque_current)
    manager.add_element(axis_torque_limit)
    manager.add_element(motor_status)
    # manager.add_element(motor_faults)

    # manager.add_element(logger)

    # Create a serial thread
    serial_thread = create_serial_thread()
    data_keys = [ 
        "position",
        "velocity",
        "motor_speed",
        "torque_limit",
        "torque_current",
        "status",
        "faults",
        "controller_state",
        "padding"
    ]

    decoder = StructDecoder(data_keys=data_keys, packet_format="<dddddiiii")
    validator = WindowValidator(window_size=58, start_byte=0xA5, end_byte=0x5A)

    # Start serial manager and subscriber
    server = SerialUpdateServer(
        manager,
        serial_instance=serial_thread,
        decoder=decoder,
        validator=validator,
    )

    # Create the task to update the monitor manager at a fixed rate
    asyncio.create_task(
        manager.update_fixed_rate(frequency=20)
    )  # Updates every 1 second

    # Start the ZeroMQ subscriber (it will process updates asynchronously)
    await server.start(frequency=20)


if __name__ == "__main__":
    asyncio.run(main())