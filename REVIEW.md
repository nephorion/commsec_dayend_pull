# Code Review

## Critical Bugs

### 1. `get_date_range` — start/end swapped in `pd.date_range`
**File:** `src/app.py:96`

`start` and `end` are reversed, so any range where `from < to` returns an empty list. Only `/backfill/at/` works because both dates are the same.

```python
# Current (broken)
date_range = pd.date_range(start=to_date, end=from_date)

# Fix
date_range = pd.date_range(start=from_date, end=to_date)
```

---

### 2. SQL injection in `delete_records_in_bq`
**File:** `src/app.py:125-129`

Filename is interpolated directly into a SQL string. If a filename ever contains a quote, the query breaks (or worse).

```python
# Current (unsafe)
delete_query = f"DELETE FROM `data.raw_eod` WHERE filename = '{filename}'"

# Fix — use a parameterized query
delete_query = "DELETE FROM `data.raw_eod` WHERE filename = @filename"
job_config = bigquery.QueryJobConfig(
    query_parameters=[bigquery.ScalarQueryParameter("filename", "STRING", filename)]
)
bq_client.query(delete_query, job_config=job_config).result()
```

---

### 3. Extra CSV columns cause `IndexError`
**File:** `src/app.py:147`

The dict comprehension iterates all columns with `enumerate(columns)`, then looks up `field_names[i]`. If the file ever has more than 7 columns, `field_names[i]` raises `IndexError`.

```python
# Current (fragile)
json_record = {f"{field_names[i]}": value for i, value in enumerate(columns)}

# Fix — only map the first N fields
json_record = {field_names[i]: columns[i] for i in range(len(field_names))}
```

---

### 4. Trailing `\r` on last column value (CRLF line endings)
**File:** `src/app.py:141`

`split('\n')` on CRLF content leaves `\r` on the last column (`volume`). The `file_contents.strip()` only removes leading/trailing content from the whole file, not per row.

```python
# Fix — strip each row
rows = file_contents.strip().splitlines()
# then strip each column value
columns = [c.strip() for c in row.split(',')]
```

---

## Reliability Issues

### 5. All exceptions swallowed — routes always return 200
**File:** `src/app.py:240-241`

`get_eod_data` catches all exceptions and logs them, but the caller always gets a 200. A failed run looks identical to a successful one from the caller's perspective.

```python
# Fix — return a flag and reflect it in the response
def get_eod_data(dates):
    ...
    except Exception as e:
        logger.error(f"Failed to get eod data [{e}]")
        return False
    ...
    return True

@app.route('/backfill/from/<from_date_str>/to/<to_date_str>')
def backfill(from_date_str, to_date_str):
    dates = get_date_range(from_date_str, to_date_str)
    ok = get_eod_data(dates)
    status = 200 if ok else 500
    return make_response(jsonify({"dates": dates}), status)
```

---

### 6. Cloud Run request timeout on large backfills
**File:** `src/app.py:208-244`

Everything runs synchronously within the HTTP request. Cloud Run has a maximum 60-minute request timeout. A multi-year backfill via Selenium will exceed this. The response returns only after all work is done.

**Fix:** Use Cloud Tasks or Pub/Sub to enqueue individual dates as separate jobs, or break the backfill into smaller chunks that each complete within the timeout.

---

### 7. One GCS API call per date in `file_exists_in_bucket`
**File:** `src/app.py:58-60`

For a 5-year backfill (~1300 dates) this makes ~1300 individual GCS HEAD requests.

```python
# Fix — fetch all existing GCS files once upfront and pass the set in
def get_eod_data(dates):
    ...
    gcs_files_set = set(list_files_with_prefix(bucket, 'eod/'))
    for date in dates:
        process_date(browser, bucket, date, holidays, gcs_files_set)

def process_date(browser, bucket, date, holidays, existing_files):
    ...
    if make_file_name('eod/', date) not in existing_files:
        # download and upload
```

---

### 8. GCP clients created on every request
**File:** `src/app.py:211-214`, `src/app.py:255-257`

`bigquery.Client()`, `storage.Client()`, `secretmanager.SecretManagerServiceClient()`, and `pubsub_v1.PublisherClient()` are all instantiated fresh on every HTTP request. These are expensive to construct and should be module-level singletons.

```python
# At module level, after env var setup
storage_client = storage.Client()
bq_client = bigquery.Client()
secrets_client = secretmanager.SecretManagerServiceClient()
publisher = pubsub_v1.PublisherClient()
```

---

### 9. `holidays` is a list — O(n) lookup per date
**File:** `src/app.py:108`, `src/app.py:188`

`date_str in holidays` does a linear scan. Should be a set.

```python
# Fix
return set(str(row["date"]) for row in rows)
```

---

## Code Quality Issues

### 10. `pandas` used only for `date_range`
**File:** `src/app.py:5`, `src/app.py:96`

`pandas` is a large dependency (~30MB) used for a single call. Python's stdlib handles this fine.

```python
from datetime import date, timedelta

def get_date_range(from_date_str, to_date_str):
    from_date = parse_date_str(from_date_str)
    to_date = parse_date_str(to_date_str)
    delta = (to_date - from_date).days
    return [from_date + timedelta(days=i) for i in range(delta + 1)]
```

---

### 11. `close_browser` unconditional 3-second sleep
**File:** `src/commsec_download.py:124`

`time.sleep(3)` runs before `browser.quit()` on every request, even when no download was attempted. The download wait is already handled by `wait_for_file`. This adds 3 seconds to every request unnecessarily.

---

### 12. Dead code — `delete_records_in_bq` and `files_to_delete`
**File:** `src/app.py:122-130`, `src/app.py:135`, `src/app.py:165`

`delete_records_in_bq` is defined but never called. The `files_to_delete` logic is commented out. Either implement it or remove it.

---

### 13. `process_date` inconsistent return values
**File:** `src/app.py:179-205`

Returns `False` for weekends and holidays, but `None` (implicitly) for all other cases (success or download error). Not used by callers currently, but confusing.

---

### 14. Health check route logs on every call
**File:** `src/app.py:249`

`logger.info('This is an info log message')` is a placeholder that was never cleaned up. Cloud Run health checks hit `/` frequently, flooding logs with noise.

```python
# Fix — remove the log line
@app.route('/')
def home():
    return "ok"
```

---

### 15. `/sync` response count computed before sync runs
**File:** `src/app.py:261`

`len(set(gcs_files) - set(bq_files))` reflects the number of files that *should* be synced, not the number that *were* synced (some may fail). `sync_gcs_to_bq` should return a count of successfully inserted files.

---

## Dependency Issues

### 16. `google-cloud-*` packages have no version pins
**File:** `pyproject.toml:10-14`

`google-cloud-storage`, `google-cloud-bigquery`, etc. float to latest on every build. This can silently break the service when GCP releases breaking changes.

```toml
# Fix — add version constraints
"google-cloud-storage>=2.16,<3",
"google-cloud-bigquery>=3.20,<4",
```

---

### 17. `python-dotenv` is a production dependency
**File:** `pyproject.toml:9`

`python-dotenv` is only used in the `if __name__ == '__main__'` block of `commsec_download.py` for local testing. It should be a dev dependency.

```toml
[dependency-groups]
dev = ["python-dotenv~=1.0.1"]
```

---

## Docker Issues

### 18. No `.dockerignore`
**File:** `Dockerfile`

`COPY . .` copies `.venv`, `__pycache__`, `.git`, any locally downloaded `.txt` files, and other unnecessary content into the image, increasing image size and potentially leaking local state.

```
# .dockerignore
.venv/
.git/
__pycache__/
src/__pycache__/
*.txt
.env
```
