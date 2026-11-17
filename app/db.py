import argparse
import csv
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "processed" / "civicos.db"
SAMPLE_PATH = ROOT / "data" / "sample" / "nyc311_2026-10_first10000.csv"
FIELDS = (
    "unique_key", "created_date", "closed_date", "borough",
    "complaint_type", "status", "latitude", "longitude",
)
HOUR = "CAST(substr(created_date, 12, 2) AS INTEGER)"
MAP_COORDINATES = "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180"


def get_db_path():
    configured = os.environ.get("CIVICOS_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_DB_PATH


def import_csv(csv_path, db_path=DEFAULT_DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("CSV is missing one or more NYC 311 columns.")

        def rows():
            for line, row in enumerate(reader, start=2):
                values = [(row[field] or "").strip() or None for field in FIELDS]
                key, created = values[:2]
                if not key or not created:
                    raise ValueError(f"Missing ID or creation time at CSV line {line}.")
                # Keep dates in New York time.
                for index in (1, 2):
                    if values[index]:
                        timestamp = datetime.fromisoformat(values[index])
                        if timestamp.tzinfo is not None:
                            timestamp = timestamp.astimezone(ZoneInfo("America/New_York"))
                        values[index] = timestamp.replace(tzinfo=None).isoformat()
                local_date = values[1][:10]
                # Bad coordinates stay in the totals, but won't show on the map.
                for index, bound in ((6, 90), (7, 180)):
                    try:
                        number = float(values[index])
                        values[index] = number if -bound <= number <= bound else None
                    except (TypeError, ValueError):
                        values[index] = None
                yield (*values, local_date)

        with closing(sqlite3.connect(db_path)) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS service_requests (
                    unique_key TEXT PRIMARY KEY NOT NULL,
                    created_date TEXT NOT NULL,
                    closed_date TEXT,
                    borough TEXT,
                    complaint_type TEXT,
                    status TEXT,
                    latitude REAL,
                    longitude REAL,
                    local_date TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_requests_date_borough
                ON service_requests (local_date, borough)
            """)
            cursor = connection.executemany("""
                INSERT INTO service_requests (
                    unique_key, created_date, closed_date, borough,
                    complaint_type, status, latitude, longitude, local_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(unique_key) DO NOTHING
            """, rows())
            return cursor.rowcount


def query(columns, conditions=(), params=(), suffix=""):
    sql = f"SELECT {columns} FROM service_requests"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    # SQL fragments are defined here. User selections are bound as parameters.
    db_path = get_db_path()
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as connection:
        return pd.read_sql_query(sql + suffix, connection, params=params)


def get_date_bounds():
    result = query("MIN(local_date) AS first_day, MAX(local_date) AS last_day")
    return tuple(result.iloc[0])


def date_filter(start_date, end_date):
    conditions, params = [], []
    if start_date is not None and end_date is not None and str(start_date) > str(end_date):
        raise ValueError("Start date must come before end date.")
    if start_date is not None:
        conditions.append("local_date >= ?")
        params.append(str(start_date))
    if end_date is not None:
        conditions.append("local_date <= ?")
        params.append(str(end_date))
    return conditions, params


def map_filter(borough, complaint_type, start_date, end_date):
    conditions, params = date_filter(start_date, end_date)
    conditions.append(MAP_COORDINATES)
    if borough != "All":
        conditions.append("borough = ?")
        params.append(borough)
    if complaint_type != "All":
        conditions.append("complaint_type = ?")
        params.append(complaint_type)
    return conditions, params


def options(column, conditions, params):
    conditions = [*conditions, f"{column} IS NOT NULL"]
    result = query(f"DISTINCT {column}", conditions, params, f" ORDER BY {column}")
    return result[column].tolist()


def get_map_boroughs(start_date=None, end_date=None):
    conditions, params = map_filter("All", "All", start_date, end_date)
    return options("borough", conditions, params)


def get_map_complaint_types(borough, start_date=None, end_date=None):
    conditions, params = map_filter(borough, "All", start_date, end_date)
    return options("complaint_type", conditions, params)


def get_map_points(borough, complaint_type, start_date=None, end_date=None):
    conditions, params = map_filter(borough, complaint_type, start_date, end_date)
    return query("latitude, longitude, borough, complaint_type", conditions, params)



def get_map_counts(borough, complaint_type, start_date=None, end_date=None):
    conditions, params = map_filter(borough, complaint_type, start_date, end_date)
    conditions.remove(MAP_COORDINATES)
    result = query(
        f"COUNT(*) AS total, COUNT(CASE WHEN {MAP_COORDINATES} THEN 1 END) AS geocoded",
        conditions, params
    ).iloc[0]
    return int(result["total"]), int(result["geocoded"])


def get_map_preview(borough, complaint_type, start_date, end_date, limit):
    conditions, params = map_filter(borough, complaint_type, start_date, end_date)
    # Use the same order each time so the preview doesn't jump around.
    return query(
        "unique_key, created_date, latitude, longitude, borough, complaint_type",
        conditions, [*params, int(limit)],
        " ORDER BY created_date, unique_key LIMIT ?"
    )


def get_data_info():
    return query(
        f"COUNT(*) AS total, MIN(created_date) AS first_record, "
        f"MAX(created_date) AS last_record, "
        f"COUNT(CASE WHEN {MAP_COORDINATES} THEN 1 END) AS geocoded"
    ).iloc[0].to_dict()


def dashboard_filter(boroughs, statuses, start_hour, end_hour, start_date, end_date):
    conditions, params = date_filter(start_date, end_date)
    for column, selected in (("borough", boroughs), ("status", statuses)):
        if selected is None:
            continue
        if not selected:
            conditions.append("0 = 1")
            continue
        placeholders = ", ".join(["?"] * len(selected))
        conditions.append(f"{column} IN ({placeholders})")
        params.extend(selected)
    conditions.append(f"{HOUR} BETWEEN ? AND ?")
    params.extend((start_hour, end_hour))
    return conditions, params


def get_dashboard_boroughs(start_date=None, end_date=None):
    conditions, params = date_filter(start_date, end_date)
    return options("borough", conditions, params)


def get_dashboard_statuses(boroughs, start_date=None, end_date=None):
    conditions, params = dashboard_filter(boroughs, None, 0, 23, start_date, end_date)
    return options("status", conditions, params)


def get_dashboard_complaint_types(
    boroughs, statuses, start_hour, end_hour, start_date=None, end_date=None
):
    conditions, params = dashboard_filter(
        boroughs, statuses, start_hour, end_hour, start_date, end_date
    )
    return options("complaint_type", conditions, params)


def close_hours(frame):
    created = pd.to_datetime(frame["created_date"], format="mixed", errors="coerce")
    closed = pd.to_datetime(frame["closed_date"], format="mixed", errors="coerce")
    return (closed - created).dt.total_seconds() / 3600


def get_dashboard_requests(
    boroughs, statuses, start_hour, end_hour, complaint_type,
    start_date=None, end_date=None
):
    conditions, params = dashboard_filter(
        boroughs, statuses, start_hour, end_hour, start_date, end_date
    )
    if complaint_type != "All":
        conditions.append("complaint_type = ?")
        params.append(complaint_type)
    frame = query(", ".join(FIELDS) + f", {HOUR} AS hour", conditions, params, " ORDER BY rowid")
    frame["hours"] = close_hours(frame)
    return frame


def get_dashboard_baseline(start_date=None, end_date=None):
    conditions, params = date_filter(start_date, end_date)
    result = query(
        "COUNT(*) AS total, COUNT(CASE WHEN status = 'Closed' THEN 1 END) AS closed, "
        "MAX(created_date) AS latest", conditions, params
    ).iloc[0]
    closed = query(
        "created_date, closed_date",
        [*conditions, "status = 'Closed'", "closed_date IS NOT NULL"], params
    )
    hours = close_hours(closed)
    latest = result["latest"]
    return {
        "total": int(result["total"]),
        "closed_rate": 100 * result["closed"] / result["total"] if result["total"] else 0,
        "median": hours[hours >= 0].median(),
        "last_hour": int(latest[11:13]) if latest else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import NYC 311 rows into SQLite.")
    parser.add_argument("csv_path", nargs="?", type=Path, default=SAMPLE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    inserted = import_csv(args.csv_path, args.output)
    with closing(sqlite3.connect(args.output)) as connection:
        total = connection.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0]
    print(f"Inserted {inserted:,} new rows. Database contains {total:,} requests.")
    print(f"Database: {args.output.resolve()}")
