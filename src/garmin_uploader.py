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
    """Authenticate and return Garmin client.
    
    Supports two authentication methods:
    1. Session token (GARMIN_SESSION) - preferred, avoids login issues
    2. Email + password - fallback, may trigger CAPTCHA
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    session_token = os.environ.get("GARMIN_SESSION")

    # Method 1: Try session token first (more reliable)
    if session_token:
        try:
            import json
            token_data = json.loads(session_token)
            client = Garmin(email or "", password or "")
            client.login(token_data)
            print("✓ Successfully authenticated with session token")
            return client
        except Exception as e:
            print(f"Warning: Session token auth failed: {e}")
            print("Falling back to email/password...")

    # Method 2: Email + password
    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables required")
        print("       Or provide GARMIN_SESSION token for more reliable auth")
        sys.exit(1)

    try:
        client = Garmin(email, password)
        client.login()
        print("✓ Successfully logged into Garmin Connect")
        
        # Print session token for future use (user can save this)
        try:
            token = client.garth.dumps()
            print("\n💡 TIP: Save this session token as GARMIN_SESSION secret for more reliable auth:")
            print(f"   (Token is ~2000 chars, starts with: {token[:50]}...)")
        except Exception:
            pass
            
        return client
    except Exception as e:
        print(f"Error logging into Garmin Connect: {e}")
        print("\nTroubleshooting:")
        print("  1. Check email/password are correct")
        print("  2. Try logging into Garmin Connect manually first")
        print("  3. If you have 2FA enabled, you may need to use session tokens")
        print("  4. Garmin may be rate-limiting - try again in a few minutes")
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


def check_duplicate(client: Garmin, start_time: datetime, duration_seconds: int) -> bool:
    """Check if an activity with similar start time already exists in Garmin."""
    try:
        # Get activities from the same day
        date_str = start_time.strftime("%Y-%m-%d")
        activities = client.get_activities_by_date(date_str, date_str)

        if not activities:
            return False

        # Check for activities with similar start time (within 5 minutes)
        for activity in activities:
            activity_start = activity.get("startTimeLocal", "")
            if not activity_start:
                continue

            try:
                existing_start = date_parser.parse(activity_start)
                time_diff = abs((existing_start.replace(tzinfo=None) - start_time.replace(tzinfo=None)).total_seconds())

                # If start times are within 5 minutes, consider it a duplicate
                if time_diff < 300:
                    print(f"⚠ Duplicate detected: Activity '{activity.get('activityName')}' "
                          f"started at {activity_start}")
                    return True
            except Exception:
                continue

        return False

    except Exception as e:
        print(f"Warning: Could not check for duplicates: {e}")
        # If we can't check, proceed with upload (better to have duplicate than miss)
        return False


def upload_activity(
    client: Garmin,
    name: str,
    activity_type: str,
    duration_seconds: int,
    start_time: datetime,
    calories: int = 0,
    skip_duplicate_check: bool = False,
) -> None:
    """Upload a manual activity to Garmin Connect."""

    garmin_type = get_activity_type(activity_type)

    # Format start time for Garmin API
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    print(f"\nActivity details:")
    print(f"  Name: {name}")
    print(f"  Type: {garmin_type['typeKey']} (ID: {garmin_type['typeId']})")
    print(f"  Duration: {duration_seconds // 60} minutes")
    print(f"  Start Time: {start_time_str}")
    print(f"  Calories: {calories}")

    # Check for duplicates before uploading
    if not skip_duplicate_check:
        print("\nChecking for duplicates in Garmin...")
        if check_duplicate(client, start_time, duration_seconds):
            print("\n⏭ Skipping upload: Activity already exists in Garmin Connect")
            return

    print("\nUploading to Garmin Connect...")

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
    parser.add_argument("--skip-duplicate-check", action="store_true", 
                        help="Skip checking for duplicate activities")

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

    # Upload activity (with duplicate check by default)
    upload_activity(
        client=client,
        name=args.name,
        activity_type=args.activity_type,
        duration_seconds=duration_seconds,
        start_time=start_time,
        calories=calories,
        skip_duplicate_check=args.skip_duplicate_check,
    )

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()

