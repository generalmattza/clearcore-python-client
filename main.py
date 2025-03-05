#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-01-01
# version ='0.0.1'
# ---------------------------------------------------------------------------
"""a_short_project_description"""
# ---------------------------------------------------------------------------

import argparse
import asyncio
from datetime import datetime
from logging.config import dictConfig

# Import the load_configs function
from config_loader import load_configs
from app_monitor.text_formatter import TextFormat

from app_monitor import (
    TerminalManager,
    RangeBar,
    SerialUpdateServer,
)
from app_monitor.elements_base import IndicatorLamp
from motor_states import MotorStatusElement, MotorAlertElement, ColoredRangeBar
from app_monitor.server import StructDecoder, WindowValidator
from threadsafe_serial import ThreadSafeSerial


LOGGING_CONFIG_FILEPATH = "config/logger.yaml"

# Load user configurations using the config_loader module
logging_config = load_configs(LOGGING_CONFIG_FILEPATH)

# Configure logging using the specified logging configuration
dictConfig(logging_config)

# Define the default filename for saving control log data
CONTROL_LOGDATA_FILENAME = f"control_logdata_{datetime.now().strftime(r"%Y%m%d")}.csv"

def parse_arguments():
    """Parse command-line arguments to select the COM port."""
    parser = argparse.ArgumentParser(description="Monitor application for serial communication.")
    parser.add_argument(
        "--port",
        type=str,
        required=False,
        default="COM6",
        help="Specify the COM port for serial communication (e.g., COM6, /dev/ttyUSB0)."
    )
    parser.add_argument(
        "--file",
        type=str,
        required=False,
        default=CONTROL_LOGDATA_FILENAME,
        help="Specify the base filename for saving motor data."
    )
    return parser.parse_args()


def create_serial_thread(port):
    """Create a ThreadSafeSerial instance with the given port."""
    threadsafe_serial = ThreadSafeSerial(
        port=port,
        baudrate=115200,
        timeout=3,
    )
    return threadsafe_serial


async def main():
    """Main function for running the application."""
    args = parse_arguments()  # Get command-line arguments

    # Create a MonitorManager instance
    manager = TerminalManager(log_to_file_enabled=True)
    manager.init_csv_logger(filename=args.file)

    # Add a progress bar and table elements with formatting
    BAR_WIDTH = 30
    text_format = TextFormat(bold=True)

    # Example instantiation of the RangeBar
    axis_properties = dict(
        text_format=text_format,
        max_label_length=12,
        max_display_length=5,
        marker_trace="█",
        range_trace="-",
        digits=1,
    )

    position = RangeBar(
        element_id="position", label="Axis Position", unit="mm", min_value=0,
        max_value=1000, **axis_properties
    )
    axis_velocity = RangeBar(
        element_id="velocity", label="Axis Vel", unit="mm/min", min_value=-100,
        max_value=100, **axis_properties
    )
    motor_speed = RangeBar(
        element_id="motor_speed", label="Motor Speed", unit="rpm", min_value=-1500,
        max_value=1500, **axis_properties
    )
    axis_torque_current = ColoredRangeBar(
        element_id="torque_current", label="Torque", unit="%", min_value=-100,
        max_value=100, **axis_properties
    )
    axis_torque_limit = RangeBar(
        element_id="torque_limit", label="Torque Limit", unit="%", min_value=0,
        max_value=100, **axis_properties
    )
    velocity_command = RangeBar(
        element_id="velocity_command", label="Velocity command", unit="-", min_value=0,
        max_value=1, enabled=False, **axis_properties
    )
    torque_command = RangeBar(
        element_id="torque_command", label="Torque command", unit="-", min_value=0,
        max_value=1, enabled=False, **axis_properties
    )

    motor_status = MotorStatusElement(element_id="status", static_text="Motor Status: ")
    up_button = IndicatorLamp(element_id="up_button", label="UP", off_color="grey")
    down_button = IndicatorLamp(element_id="down_button", label="DOWN", off_color="grey")
    clear_faults_button = IndicatorLamp(element_id="clear_faults_button", label="CLEAR FAULTS", off_color="grey")
    zero_axis_button = IndicatorLamp(element_id="zero_axis_button", label="ZERO AXIS", off_color="grey")
    estop_button = IndicatorLamp(element_id="estop_button", label="E-STOP", on_color="red", off_color="grey")
    motor_faults = MotorAlertElement(element_id="faults", enabled=False, static_text="Faults: ")

    manager.add_element(position)
    manager.add_element(axis_velocity)
    manager.add_element(motor_speed)
    manager.add_element(axis_torque_current)
    manager.add_element(axis_torque_limit)
    manager.add_element(motor_status)
    manager.add_element(motor_faults)
    manager.add_element(velocity_command)
    manager.add_element(torque_command)
    manager.add_element(up_button)
    manager.add_element(down_button)
    manager.add_element(clear_faults_button)
    manager.add_element(zero_axis_button)
    manager.add_element(estop_button)

    # Create a serial thread with the user-specified COM port
    serial_thread = create_serial_thread(port=args.port)
    data_keys = [
        "position",
        "velocity",
        "motor_speed",
        "torque_current",
        "torque_limit",
        "velocity_command",
        "torque_command",
        "status",
        "faults",
        "up_button",
        "down_button",
        "clear_faults_button",
        "zero_axis_button",
        "estop_button",
    ]

    validator = WindowValidator(window_size=74, start_byte=0xA5, end_byte=0x5A)
    decoder = StructDecoder(data_keys=data_keys, packet_format="<dddddddii?????xxx")

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
