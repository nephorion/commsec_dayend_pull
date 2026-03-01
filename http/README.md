# HTTP Test Scenarios

PyCharm HTTP Client test files for the `commsec-dayend-pull` REST endpoints.

## Files

| File | Purpose |
|------|---------|
| `endpoints.http` | Test scenarios for all endpoints |
| `http-client.env.json` | Shared environment variables (`local`, `prod`) |
| `http-client.private.env.json` | Secret values (tokens) — do not commit |

## Running Tests in PyCharm

1. Open `endpoints.http`
2. Select an environment from the dropdown in the top-right of the editor (`local` or `prod`)
3. Click the green run arrow in the gutter next to any request

## Environments

### local

Targets `http://localhost:8080`. No auth required.

Start the local server first:
```bash
flask --app app run --port 8080
```

### prod

Targets the Cloud Run service. Requires a valid identity token.

1. Get the service URL and set it in `http-client.env.json`:
```bash
gcloud run services describe commsec-dayend-pull \
  --platform managed \
  --region australia-southeast1 \
  --format 'value(status.url)'
```

2. Get an identity token and set it in `http-client.private.env.json`:
```bash
gcloud auth print-identity-token
```

## Endpoints

| Request | Description |
|---------|-------------|
| `GET /` | Health check |
| `GET /backfill/at/today` | Download today's data |
| `GET /backfill/at/yesterday` | Download yesterday's data |
| `GET /backfill/at/YYYYMMDD` | Download data for a specific date |
| `GET /backfill/from/YYYYMMDD/to/YYYYMMDD` | Download data for a date range |
