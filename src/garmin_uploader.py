#!/usr/bin/env python3
"""
Upload activities to Garmin Connect.

This script receives activity data (typically from Strava via n8n webhook)
and uploads it to Garmin Connect as a manual activity.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from dateutil import parser as date_parser
from garminconnect import Garmin


# Mapping from Strava activity types to Garmin activity types
# Garmin activity type IDs: https://connect.garmin.com/modern/main/js/properties/activity_types/activity_types.properties
ACTIVITY_TYPE_MAP = {
    "weight_training": {
        "typeId": 13,  # Strength Training
        "typeKey": "strength_training",
    },
    "strength_training": {
        "typeId": 13,
        "typeKey": "strength_training",
    },
    "workout": {
        "typeId": 13,  # Default workouts to strength training
        "typeKey": "strength_training",
    },
    "crossfit": {
        "typeId": 13,
        "typeKey": "strength_training",
    },
    "yoga": {
        "typeId": 106,
        "typeKey": "yoga",
    },
    "pilates": {
        "typeId": 107,
        "typeKey": "pilates",
    },
}


def get_garmin_client() -> Garmin:
    """Authenticate and return Garmin client."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables required")
        sys.exit(1)

    try:
        client = Garmin(email, password)
        client.login()
        print("✓ Successfully logged into Garmin Connect")
        return client
    except Exception as e:
        print(f"Error logging into Garmin Connect: {e}")
        sys.exit(1)


def parse_duration(duration_str: str) -> int:
    """Parse duration string to seconds."""
    try:
        return int(float(duration_str))
    except (ValueError, TypeError):
        print(f"Warning: Could not parse duration '{duration_str}', defaulting to 3600")
        return 3600


def parse_start_time(start_time_str: str | None) -> datetime:
    """Parse start time string to datetime, or return current time."""
    if not start_time_str:
        return datetime.now(timezone.utc)

    try:
        dt = date_parser.parse(start_time_str)
        # Ensure timezone aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception as e:
        print(f"Warning: Could not parse start time '{start_time_str}': {e}")
        return datetime.now(timezone.utc)


def get_activity_type(activity_type_str: str) -> dict:
    """Map activity type string to Garmin activity type."""
    normalized = activity_type_str.lower().replace(" ", "_").replace("-", "_")

    if normalized in ACTIVITY_TYPE_MAP:
        return ACTIVITY_TYPE_MAP[normalized]

    # Default to strength training for unknown types
    print(f"Warning: Unknown activity type '{activity_type_str}', defaulting to strength_training")
    return ACTIVITY_TYPE_MAP["strength_training"]


def upload_activity(
    client: Garmin,
    name: str,
    activity_type: str,
    duration_seconds: int,
    start_time: datetime,
    calories: int = 0,
) -> None:
    """Upload a manual activity to Garmin Connect."""

    garmin_type = get_activity_type(activity_type)

    # Format start time for Garmin API
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    print(f"\nUploading activity to Garmin Connect:")
    print(f"  Name: {name}")
    print(f"  Type: {garmin_type['typeKey']} (ID: {garmin_type['typeId']})")
    print(f"  Duration: {duration_seconds // 60} minutes")
    print(f"  Start Time: {start_time_str}")
    print(f"  Calories: {calories}")

    try:
        # Create manual activity
        response = client.add_manual_activity(
            activity_name=name,
            activity_type_id=garmin_type["typeId"],
            start_time=start_time_str,
            duration_seconds=duration_seconds,
            calories=calories if calories > 0 else None,
            description="Synced from Fitbod via Strava",
        )

        print(f"\n✓ Activity uploaded successfully!")
        print(f"  Activity ID: {response.get('activityId', 'unknown')}")

    except Exception as e:
        print(f"\n✗ Error uploading activity: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload activity to Garmin Connect")
    parser.add_argument("--name", required=True, help="Activity name")
    parser.add_argument("--type", dest="activity_type", required=True, help="Activity type")
    parser.add_argument("--duration", required=True, help="Duration in seconds")
    parser.add_argument("--start-time", help="Start time (ISO format)")
    parser.add_argument("--calories", default="0", help="Calories burned")

    args = parser.parse_args()

    print("=" * 50)
    print("Fitbod → Garmin Sync")
    print("=" * 50)

    # Parse inputs
    duration_seconds = parse_duration(args.duration)
    start_time = parse_start_time(args.start_time)
    calories = int(args.calories) if args.calories else 0

    # Authenticate with Garmin
    client = get_garmin_client()

    # Upload activity
    upload_activity(
        client=client,
        name=args.name,
        activity_type=args.activity_type,
        duration_seconds=duration_seconds,
        start_time=start_time,
        calories=calories,
    )

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()

