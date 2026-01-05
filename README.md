# Fitbod → Garmin Sync

Automatically sync your Fitbod strength training workouts to Garmin Connect via Strava.

## Problem

Fitbod doesn't have native Garmin Connect integration, which means:
- Strength workouts don't appear in Garmin
- Body Battery doesn't account for gym sessions
- Recovery metrics are inaccurate

## Solution

Since Fitbod already syncs to Strava automatically, we bridge the gap:

```
Fitbod → Strava → [n8n + GitHub Actions] → Garmin Connect
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n Cloud Workflow                          │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │ Schedule │──▶│  Strava  │──▶│  Filter  │──▶│ HTTP Request│  │
│  │ (30 min) │   │  Get     │   │  Weight  │   │ POST to     │  │
│  │          │   │ Activities│   │ Training │   │ GitHub API  │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬──────┘  │
└──────────────────────────────────────────────────────┼──────────┘
                                                       │
                          repository_dispatch webhook  │
                                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions                              │
│                                                                 │
│  Receives activity data → Python script → Upload to Garmin     │
└─────────────────────────────────────────────────────────────────┘
```

## Setup

### Step 1: GitHub Repository Setup

1. **Fork or clone this repo** to your GitHub account

2. **Add GitHub Secrets** (Settings → Secrets → Actions):

   | Secret | Description |
   |--------|-------------|
   | `GARMIN_EMAIL` | Your Garmin Connect email |
   | `GARMIN_PASSWORD` | Your Garmin Connect password |

3. **Create a Personal Access Token** for n8n to trigger workflows:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `repo` scope
   - Save this token for n8n setup

### Step 2: Strava API Setup

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application:
   - Application Name: `Fitbod Garmin Sync`
   - Website: `https://github.com`
   - Authorization Callback Domain: Your n8n instance URL
3. Note your **Client ID** and **Client Secret**

### Step 3: n8n Workflow Setup

Create a new workflow in n8n with these nodes:

#### Node 1: Schedule Trigger
- **Type:** Schedule Trigger
- **Interval:** Every 30 minutes

#### Node 2: Strava - Get Activities
- **Type:** Strava node
- **Operation:** Get Many Activities
- **Credentials:** Connect your Strava account (OAuth)
- **Return All:** false
- **Limit:** 5

#### Node 3: Filter - Weight Training Only
- **Type:** IF node
- **Condition:** `{{ $json.type }}` equals `WeightTraining`

#### Node 4: HTTP Request - Trigger GitHub Action
- **Type:** HTTP Request
- **Method:** POST
- **URL:** `https://api.github.com/repos/YOUR_USERNAME/fitbod-garmin/dispatches`
- **Authentication:** Header Auth
  - Name: `Authorization`
  - Value: `Bearer YOUR_GITHUB_TOKEN`
- **Headers:**
  - `Accept`: `application/vnd.github.v3+json`
- **Body (JSON):**
```json
{
  "event_type": "strava-activity",
  "client_payload": {
    "activity_name": "{{ $json.name }}",
    "activity_type": "strength_training",
    "duration_seconds": "{{ $json.elapsed_time }}",
    "start_time": "{{ $json.start_date }}",
    "calories": "{{ $json.calories || 0 }}"
  }
}
```

### Step 4: Test the Integration

1. **Manual Test:** Go to GitHub Actions → "Upload to Garmin" → "Run workflow"
   - Fill in test values
   - Check if activity appears in Garmin Connect

2. **End-to-End Test:**
   - Do a workout in Fitbod
   - Wait for Fitbod → Strava sync
   - Wait for n8n schedule (or trigger manually)
   - Check Garmin Connect for the activity

## Project Structure

```
fitbod-garmin/
├── README.md
├── LICENSE
├── requirements.txt
├── .github/
│   └── workflows/
│       └── garmin-upload.yml    # GitHub Actions workflow
└── src/
    ├── __init__.py
    └── garmin_uploader.py       # Garmin Connect upload script
```

## Filtering

Only activities matching these criteria are synced:

- **Activity Type:** `WeightTraining` (from Strava)
- **Mapped to Garmin:** Strength Training

### Supported Activity Types

| Strava Type | Garmin Type |
|-------------|-------------|
| `WeightTraining` | Strength Training |
| `Workout` | Strength Training |
| `Crossfit` | Strength Training |
| `Yoga` | Yoga |
| `Pilates` | Pilates |

## Cost

| Service | Cost |
|---------|------|
| n8n Cloud (Starter) | $24/mo |
| GitHub Actions | Free |
| Strava API | Free |
| Garmin Connect | Free |

**Execution budget:** ~1,440 executions/month (every 30 min) = 58% of n8n Starter plan

## Limitations

- **Garmin API:** Uses unofficial API via `garminconnect` library (may break with updates)
- **Data Fidelity:** Individual exercise details not transferred (only duration, calories, activity type)
- **Latency:** Up to 30-minute delay from Fitbod to Garmin
- **No Heart Rate:** Unless captured by a connected device during the workout

## Troubleshooting

### Activity not appearing in Garmin

1. Check GitHub Actions logs for errors
2. Verify Garmin credentials are correct
3. Ensure activity type is supported

### n8n not triggering

1. Check n8n execution history
2. Verify Strava OAuth is connected
3. Check filter conditions

### Garmin login fails

Garmin occasionally requires re-authentication. If this happens:
1. Try logging into Garmin Connect manually
2. Complete any security prompts
3. Re-run the workflow

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GARMIN_EMAIL="your@email.com"
export GARMIN_PASSWORD="yourpassword"

# Run manually
python src/garmin_uploader.py \
  --name "Test Workout" \
  --type "strength_training" \
  --duration 3600 \
  --calories 300
```

## Contributing

Contributions welcome! Please open an issue first to discuss changes.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) - Garmin Connect API library
- [n8n](https://n8n.io/) - Workflow automation platform
- [Strava API](https://developers.strava.com/) - Activity data source
