#!/usr/bin/env python3
"""
Battery God Mode - Forensic Battery Monitoring for macOS
=========================================================
A kernel-level battery monitoring solution that extracts raw hardware
metrics using ioreg and pushes detailed reports to Notion.

This script performs:
1. Auto-configuration of Notion database schema
2. Forensic-level data extraction via ioreg XML parsing
3. Rich Notion page creation with engineering reports

Author: Senior macOS Kernel Engineer
Date: 2026-02-01
"""

import json
import logging
import os
import plistlib
import subprocess
import sys
from datetime import datetime
from typing import Any, Optional

import requests

# =============================================================================
# Configuration
# =============================================================================

# Environment variables for sensitive data
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# Notion API configuration
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# =============================================================================
# Logging Setup
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# =============================================================================
# Part 1: Notion Database Schema Automation
# =============================================================================


def ensure_database_schema() -> bool:
    """
    Ensure the Notion database has all required properties (columns).
    Sends a PATCH request to create/update the schema.

    Returns:
        bool: True if schema was updated successfully, False if failed
              (but script should continue execution).
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        logger.warning("Missing API credentials, skipping schema update")
        return False

    logger.info("Ensuring Notion database schema is configured...")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    # Define the required database properties
    schema_properties = {
        "Real Health %": {
            "number": {
                "format": "percent",
            },
        },
        "Design Capacity (mAh)": {
            "number": {
                "format": "number",
            },
        },
        "Current Max Capacity (mAh)": {
            "number": {
                "format": "number",
            },
        },
        "Cycle Count": {
            "number": {
                "format": "number",
            },
        },
        "Temperature (C)": {
            "number": {
                "format": "number",
            },
        },
        "Voltage (V)": {
            "number": {
                "format": "number",
            },
        },
        "Amperage (mA)": {
            "number": {
                "format": "number",
            },
        },
        "Watts": {
            "number": {
                "format": "number",
            },
        },
        "Time Remaining (Min)": {
            "number": {
                "format": "number",
            },
        },
        "Charging Status": {
            "select": {
                "options": [
                    {"name": "Charging", "color": "green"},
                    {"name": "Discharging", "color": "orange"},
                    {"name": "Fully Charged", "color": "blue"},
                    {"name": "Not Charging", "color": "gray"},
                ],
            },
        },
    }

    payload = {
        "properties": schema_properties,
    }

    try:
        url = f"{NOTION_API_BASE}/databases/{NOTION_DATABASE_ID}"
        response = requests.patch(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            logger.info("✅ Database schema updated successfully")
            return True
        elif response.status_code == 403:
            logger.warning(
                "⚠️ Could not update schema (403 Forbidden). "
                "Integration may lack permissions. Continuing..."
            )
            return False
        else:
            logger.warning(
                f"⚠️ Could not update schema ({response.status_code}): "
                f"{response.text}. Continuing..."
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Schema update failed: {e}. Continuing...")
        return False


# =============================================================================
# Part 2: Forensic Data Extraction (The Secret Sauce)
# =============================================================================


def get_battery_data_forensic() -> Optional[dict[str, Any]]:
    """
    Extract forensic-level battery data using ioreg with XML parsing.
    Uses plistlib for 100% type-safe parsing.

    Returns:
        dict: Comprehensive battery metrics or None if extraction fails.
    """
    try:
        logger.info("Executing ioreg command for forensic battery extraction...")

        # Execute ioreg with XML output
        result = subprocess.run(
            ["ioreg", "-l", "-n", "AppleSmartBattery", "-r", "-a"],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"ioreg command failed: {result.stderr.decode()}")
            return None

        # Parse XML plist output
        plist_data = plistlib.loads(result.stdout)
        logger.debug(f"Raw plist data: {plist_data}")

        if not plist_data:
            logger.error("No battery data found in ioreg output")
            return None

        # Get the battery dictionary (first item in array)
        battery = plist_data[0] if isinstance(plist_data, list) else plist_data

        # === Extract Raw Keys ===

        # IDs
        serial = battery.get("Serial", "Unknown")
        device_name = battery.get("DeviceName", "Unknown")
        manufacturer = battery.get("Manufacturer", "Apple Inc.")

        # Capacity (The Absolute Truth)
        apple_raw_max_capacity = battery.get("AppleRawMaxCapacity", 0)
        design_capacity = battery.get("DesignCapacity", 0)
        nominal_charge_capacity = battery.get("NominalChargeCapacity", 0)

        # Charge
        current_capacity_pct = battery.get("CurrentCapacity", 0)  # Percentage
        apple_raw_current_capacity = battery.get("AppleRawCurrentCapacity", 0)

        # Flow (mV and mA)
        voltage_mv = battery.get("Voltage", 0)
        amperage_ma = battery.get("Amperage", 0)

        # Thermals (Raw is centi-Celsius)
        temperature_raw = battery.get("Temperature", 0)
        temperature_celsius = temperature_raw / 100.0 if temperature_raw else 0.0

        # Health
        cycle_count = battery.get("CycleCount", 0)

        # Time
        time_remaining = battery.get("TimeRemaining", 0)
        avg_time_to_empty = battery.get("AvgTimeToEmpty", 0)
        instant_time_to_empty = battery.get("InstantTimeToEmpty", 0)

        # Status
        external_connected = battery.get("ExternalConnected", False)
        is_charging = battery.get("IsCharging", False)
        fully_charged = battery.get("FullyCharged", False)

        # Adapter (optional)
        adapter_details = battery.get("AppleRawAdapterDetails", [])
        adapter_watts = 0
        if adapter_details and isinstance(adapter_details, list):
            for adapter in adapter_details:
                if isinstance(adapter, dict):
                    adapter_watts = adapter.get("Watts", 0)
                    break

        # === Calculations ===

        # Watts (Power Draw/Charge): (Voltage * Amperage) / 1_000_000 for mV*mA to W
        voltage_v = voltage_mv / 1000.0 if voltage_mv else 0
        power_watts = (voltage_mv * abs(amperage_ma)) / 1_000_000 if voltage_mv and amperage_ma else 0

        # True Wear Level: 100 - ((AppleRawMaxCapacity / DesignCapacity) * 100)
        wear_level = 0.0
        if design_capacity > 0:
            wear_level = 100.0 - ((apple_raw_max_capacity / design_capacity) * 100.0)

        # Real Health Percentage (inverse of wear)
        real_health_pct = 0.0
        if design_capacity > 0:
            real_health_pct = (apple_raw_max_capacity / design_capacity) * 100.0

        # Real Battery Percentage: (AppleRawCurrentCapacity / AppleRawMaxCapacity) * 100
        real_percentage = 0.0
        if apple_raw_max_capacity > 0:
            real_percentage = (apple_raw_current_capacity / apple_raw_max_capacity) * 100.0

        # Determine charging status
        if fully_charged:
            charging_status = "Fully Charged"
        elif is_charging:
            charging_status = "Charging"
        elif external_connected:
            charging_status = "Not Charging"
        else:
            charging_status = "Discharging"

        # Build comprehensive data dictionary
        battery_data = {
            # === IDs ===
            "serial": serial,
            "device_name": device_name,
            "manufacturer": manufacturer,
            # === Capacity ===
            "design_capacity_mah": design_capacity,
            "current_max_capacity_mah": apple_raw_max_capacity,
            "nominal_charge_capacity_mah": nominal_charge_capacity,
            # === Charge ===
            "current_capacity_pct": current_capacity_pct,
            "raw_current_capacity_mah": apple_raw_current_capacity,
            # === Flow ===
            "voltage_mv": voltage_mv,
            "voltage_v": round(voltage_v, 2),
            "amperage_ma": amperage_ma,
            "power_watts": round(power_watts, 2),
            "adapter_watts": adapter_watts,
            # === Thermals ===
            "temperature_raw": temperature_raw,
            "temperature_celsius": round(temperature_celsius, 1),
            # === Health ===
            "cycle_count": cycle_count,
            "wear_level_pct": round(wear_level, 2),
            "real_health_pct": round(real_health_pct, 2),
            "real_percentage": round(real_percentage, 2),
            # === Time ===
            "time_remaining_min": time_remaining,
            "avg_time_to_empty_min": avg_time_to_empty,
            "instant_time_to_empty_min": instant_time_to_empty,
            # === Status ===
            "external_connected": external_connected,
            "is_charging": is_charging,
            "fully_charged": fully_charged,
            "charging_status": charging_status,
            # === Metadata ===
            "timestamp": datetime.now().isoformat(),
        }

        logger.info("✅ Forensic battery data extracted successfully")
        logger.info(f"   Serial: {serial}")
        logger.info(f"   Real Health: {real_health_pct:.1f}%")
        logger.info(f"   Cycle Count: {cycle_count}")
        logger.info(f"   Temperature: {temperature_celsius:.1f}°C")
        logger.info(f"   Power: {power_watts:.2f}W ({charging_status})")

        return battery_data

    except subprocess.TimeoutExpired:
        logger.error("ioreg command timed out")
        return None
    except plistlib.InvalidFileException as e:
        logger.error(f"Failed to parse plist output: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting battery data: {e}")
        return None


# =============================================================================
# Part 3: Notion Data Injection
# =============================================================================


def build_page_children(data: dict[str, Any]) -> list[dict]:
    """
    Build the page content (children blocks) for the engineering report.

    Args:
        data: Battery data dictionary.

    Returns:
        list: List of Notion block objects.
    """
    children = []

    # === Header: Power Flow ===
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🔋 Power Flow"}}],
        },
    })

    power_items = [
        f"Voltage: {data['voltage_v']}V ({data['voltage_mv']}mV)",
        f"Amperage: {data['amperage_ma']}mA",
        f"Power Draw: {data['power_watts']}W",
        f"Status: {data['charging_status']}",
        f"External Power: {'Connected' if data['external_connected'] else 'Disconnected'}",
    ]

    for item in power_items:
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
            },
        })

    # === Header: Health Diagnostics ===
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🩺 Health Diagnostics"}}],
        },
    })

    health_items = [
        f"Real Health: {data['real_health_pct']:.1f}%",
        f"Wear Level: {data['wear_level_pct']:.1f}%",
        f"Cycle Count: {data['cycle_count']}",
        f"Temperature: {data['temperature_celsius']}°C",
    ]

    for item in health_items:
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
            },
        })

    # === Header: Capacity Analysis ===
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "📊 Capacity Analysis"}}],
        },
    })

    capacity_items = [
        f"Design Capacity: {data['design_capacity_mah']} mAh",
        f"Current Max Capacity: {data['current_max_capacity_mah']} mAh",
        f"Raw Current Charge: {data['raw_current_capacity_mah']} mAh",
        f"Real Percentage: {data['real_percentage']:.1f}%",
        f"Time Remaining: {data['time_remaining_min']} min",
    ]

    for item in capacity_items:
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
            },
        })

    # === Header: Device Info ===
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🔧 Device Information"}}],
        },
    })

    device_items = [
        f"Serial: {data['serial']}",
        f"Device Name: {data['device_name']}",
        f"Manufacturer: {data['manufacturer']}",
        f"Timestamp: {data['timestamp']}",
    ]

    for item in device_items:
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
            },
        })

    # === Divider ===
    children.append({
        "object": "block",
        "type": "divider",
        "divider": {},
    })

    # === Raw JSON Dump ===
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "📋 Raw Metrics (JSON)"}}],
        },
    })

    # Key metrics for JSON dump
    raw_metrics = {
        "serial": data["serial"],
        "cycle_count": data["cycle_count"],
        "real_health_pct": data["real_health_pct"],
        "design_capacity_mah": data["design_capacity_mah"],
        "current_max_capacity_mah": data["current_max_capacity_mah"],
        "voltage_mv": data["voltage_mv"],
        "amperage_ma": data["amperage_ma"],
        "temperature_celsius": data["temperature_celsius"],
        "power_watts": data["power_watts"],
        "charging_status": data["charging_status"],
        "timestamp": data["timestamp"],
    }

    children.append({
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [
                {"type": "text", "text": {"content": json.dumps(raw_metrics, indent=2)}}
            ],
            "language": "json",
        },
    })

    return children


def push_to_notion(data: dict[str, Any]) -> bool:
    """
    Push forensic battery data to Notion Database with rich page content.

    Args:
        data: Dictionary containing comprehensive battery metrics.

    Returns:
        bool: True if data was successfully pushed, False otherwise.
    """
    if not NOTION_API_KEY:
        logger.error("NOTION_API_KEY environment variable not set")
        return False

    if not NOTION_DATABASE_ID:
        logger.error("NOTION_DATABASE_ID environment variable not set")
        return False

    try:
        logger.info("Preparing Notion API payload with engineering report...")

        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION,
        }

        # Build page children (content)
        children = build_page_children(data)

        # Construct the payload
        payload = {
            "parent": {
                "database_id": NOTION_DATABASE_ID,
            },
            "properties": {
                # Title (Date column)
                "Date": {
                    "title": [
                        {
                            "text": {
                                "content": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            },
                        },
                    ],
                },
                # Numeric properties
                "Real Health %": {
                    "number": data["real_health_pct"] / 100.0,  # Notion percent format
                },
                "Design Capacity (mAh)": {
                    "number": data["design_capacity_mah"],
                },
                "Current Max Capacity (mAh)": {
                    "number": data["current_max_capacity_mah"],
                },
                "Cycle Count": {
                    "number": data["cycle_count"],
                },
                "Temperature (C)": {
                    "number": data["temperature_celsius"],
                },
                "Voltage (V)": {
                    "number": data["voltage_v"],
                },
                "Amperage (mA)": {
                    "number": data["amperage_ma"],
                },
                "Watts": {
                    "number": data["power_watts"],
                },
                "Time Remaining (Min)": {
                    "number": data["time_remaining_min"],
                },
                "Charging Status": {
                    "select": {
                        "name": data["charging_status"],
                    },
                },
            },
            "children": children,
        }

        logger.info("Sending forensic report to Notion...")

        url = f"{NOTION_API_BASE}/pages"
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            logger.info("✅ Successfully created forensic report in Notion!")
            return True
        elif response.status_code == 401:
            logger.error("❌ Unauthorized: Check your NOTION_API_KEY")
            logger.error(f"Response: {response.text}")
            return False
        elif response.status_code == 404:
            logger.error("❌ Not found: Check your NOTION_DATABASE_ID")
            logger.error(f"Response: {response.text}")
            return False
        elif response.status_code >= 400:
            logger.error(f"❌ API error ({response.status_code}): {response.text}")
            return False
        else:
            logger.info(f"Request completed with status {response.status_code}")
            return True

    except requests.exceptions.Timeout:
        logger.error("❌ Notion API request timed out")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ Failed to connect to Notion API. Check internet connection.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error pushing to Notion: {e}")
        return False


# =============================================================================
# Main Execution
# =============================================================================


def main() -> int:
    """
    Main function to orchestrate forensic battery monitoring.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 70)
    logger.info("🔋 Battery God Mode - Forensic Monitoring System")
    logger.info("=" * 70)

    # Step 0: Ensure database schema (non-blocking)
    ensure_database_schema()

    # Step 1: Extract forensic battery data
    logger.info("-" * 70)
    battery_data = get_battery_data_forensic()

    if battery_data is None:
        logger.error("❌ Failed to extract battery data. Exiting.")
        return 1

    # Step 2: Push data to Notion
    logger.info("-" * 70)
    success = push_to_notion(battery_data)

    if not success:
        logger.error("❌ Failed to push data to Notion. Exiting.")
        return 1

    logger.info("=" * 70)
    logger.info("🎉 Battery God Mode - Completed Successfully")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
