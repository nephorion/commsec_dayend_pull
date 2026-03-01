# commsec-dayend-pull

A Flask service that automates the download of ASX end-of-day (EOD) equity price data from CommSec. Deployed as a Google Cloud Run service triggered daily by Cloud Scheduler at 8pm AEST.

## How it works

1. Selenium logs into CommSec and navigates to the EOD download page
2. For each requested date, skips weekends and public holidays, then downloads the data file if not already in GCS
3. Uploads downloaded files to Google Cloud Storage
4. Syncs any new GCS files into BigQuery (`data.raw_eod`)
5. Publishes a completion message to a Pub/Sub topic

## Project structure

```
.
├── src/
│   ├── app.py                  # Flask app — routes, GCS/BQ sync, Pub/Sub publish
│   ├── commsec_download.py     # Selenium browser automation (login, download)
│   └── CustomException.py      # Exception wrapper
├── etc/
│   ├── dev_setup.sh            # gcloud auth setup for local dev
│   ├── raw_eod_schema.json     # BigQuery table schema
│   └── Procfile                # Process definition
├── http/                       # PyCharm HTTP test scenarios
├── holidays/                   # Public holiday data
├── companies/                  # Company reference data
├── isin/                       # ISIN reference data
├── pyproject.toml              # Dependencies (managed with uv)
├── Dockerfile                  # Container build
└── setup_pull_service.md       # Full GCP infrastructure setup guide
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/backfill/at/today` | Download today's data |
| GET | `/backfill/at/yesterday` | Download yesterday's data |
| GET | `/backfill/at/YYYYMMDD` | Download data for a specific date |
| GET | `/backfill/from/YYYYMMDD/to/YYYYMMDD` | Download data for a date range |

## Local development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Chrome or Chromium + ChromeDriver
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)

### Install dependencies

```bash
uv sync
```

This creates a `.venv` and installs all dependencies. Run this once after cloning, and again whenever `pyproject.toml` changes.

### Configure gcloud

```bash
source etc/dev_setup.sh
```

This sets the active project and logs in with Application Default Credentials so the app can access GCS, BigQuery, Secret Manager, and Pub/Sub locally.

### Environment variables

Create a `.env` file in the project root (for reference — the Flask app reads these from the environment):

```dotenv
GOOGLE_CLOUD_PROJECT=stocks-427911
BUCKET=stocks-427911
TOPIC=commsec-dayend-pull-done
PORT=8080
```

> Credentials (`COMMSEC_USER`, `COMMSEC_PASSWORD`) are fetched at runtime from Secret Manager using ADC — no need to set them locally.

### Run the server

```bash
uv run python src/app.py
```

The server starts on `http://localhost:8080`.

### Run HTTP tests

Open any file in `http/` in PyCharm, select the `local` environment from the dropdown, and click the run arrow next to a request. See [`http/README.md`](http/README.md) for details.

## GCP infrastructure

For full setup instructions (buckets, BigQuery, IAM, Cloud Run, Cloud Scheduler), see [`setup_pull_service.md`](etc/setup_pull_service.md).

### Key resources

| Resource | Name |
|----------|------|
| GCP Project | `stocks-427911` |
| Region | `australia-southeast1` |
| Cloud Run service | `commsec-dayend-pull` |
| GCS bucket | `stocks-427911` |
| BigQuery dataset | `data` |
| BigQuery table | `data.raw_eod` |
| Pub/Sub topic | `commsec-dayend-pull-done` |
| Schedule | Daily at 20:00 AEST |
