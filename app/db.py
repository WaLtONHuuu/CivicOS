import csv
import os
import sqlite3

from contextlib import closing
from datetime import datetime
from urllib.parse import quote

import pandas as pd


SAMPLE_CSV = "data/sample/nyc311_2026-10_first10000.csv"
SAMPLE_DB = "data/processed/civicos.db"


def import_sample(): # build the database from the sample CSV file
    with open(SAMPLE_CSV, "r") as source, closing(sqlite3.connect(SAMPLE_DB)) as conn:
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS service_requests (unique_key TEXT PRIMARY KEY NOT NULL, created_date TEXT NOT NULL, closed_date TEXT, complaint_type TEXT, status TEXT, borough TEXT, latitude REAL, longitude REAL, local_date TEXT NOT NULL, hour INTEGER NOT NULL, hours REAL)""") # build the table if it doesn't exist yet
            for row in csv.DictReader(source): # read each row in the csv file as a dictionary
                created = datetime.fromisoformat(row["created_date"]) # transform the created_date string into a datetime object (real time, not just int in the format YYYY-MM-DDTHH:MM:SS), really helpful while extracting the date and hour for the local_date and hour columns
                hours = None
                if row["closed_date"]:
                    closed = datetime.fromisoformat(row["closed_date"])
                    hours = (closed - created).total_seconds() / 3600
                conn.execute("""INSERT INTO service_requests(unique_key, created_date, closed_date, complaint_type, status, borough, latitude, longitude, local_date, hour, hours)VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)ON CONFLICT(unique_key) DO NOTHING""", (row["unique_key"], row["created_date"], row["closed_date"] or None, row["complaint_type"] or None, row["status"] or None, row["borough"] or None, row["latitude"] or None, row["longitude"] or None, created.date().isoformat(), created.hour, hours, )) # put the csv row values into the database with some transformations for local_date and hour
            conn.execute("CREATE INDEX IF NOT EXISTS requests_by_borough ON service_requests(borough, status, hour)") # create an index on the borough, status, and hour columns
            conn.execute("""CREATE INDEX IF NOT EXISTS closed_hours ON service_requests(hours) WHERE status = 'Closed' AND hours >= 0""") # create an index on the hours column for closed requests with valid hours
        total = conn.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0] # count the total number of requests in the database
    print(f"{total:,} requests in {SAMPLE_DB}")


def read_query(sql, params=()): # read a SQL query from the database and return the result as a pandas DataFrame
    path = os.environ.get("CIVICOS_DB_PATH", SAMPLE_DB) # get the database path from the environment variable or use the sample database if not set
    with closing(sqlite3.connect(path)) as conn:
        return pd.read_sql_query(sql, conn, params=params)


MAP_ROWS = "FROM service_requests WHERE latitude IS NOT NULL AND longitude IS NOT NULL" # only complaints with a latitude and longitude can be shown on the map


def get_map_boroughs(): # options for the borough dropdown on the map page
    sql = "SELECT borough " + MAP_ROWS + " AND borough IS NOT NULL GROUP BY borough ORDER BY MIN(rowid)"
    return read_query(sql)["borough"].tolist()


def get_map_complaint_types(borough): # options for the complaint type dropdown on the map page
    sql = "SELECT DISTINCT complaint_type " + MAP_ROWS + " AND complaint_type IS NOT NULL"
    params = []
    if borough != "All":
        sql += " AND borough = ?"
        params.append(borough)
    return read_query(sql + " ORDER BY complaint_type", params)["complaint_type"].tolist()


def get_map_points(borough, complaint_type): # provide the points to plot on the map, filtered by borough and complaint type
    sql = "SELECT latitude, longitude, borough, complaint_type " + MAP_ROWS
    params = []
    if borough != "All":
        sql += " AND borough = ?"
        params.append(borough)
    if complaint_type != "All":
        sql += " AND complaint_type = ?"
        params.append(complaint_type)
    return read_query(sql + " ORDER BY rowid", params)


def get_boroughs(): # list all boroughs in the database, for the dashboard page
    return read_query("""SELECT DISTINCT borough FROM service_requests WHERE borough IS NOT NULL ORDER BY borough""")["borough"].tolist()


def selected_values(column, values): # if user selects no values, return a SQL condition that will never be true; otherwise return a SQL condition that checks if the column is in the selected values
    if not values:
        return "0"
    marks = ", ".join("?" for value in values)
    return f"{column} IN ({marks})"


def get_statuses(boroughs): # check which statuses are present in the selected boroughs, for the dashboard page
    sql = "SELECT DISTINCT status FROM service_requests WHERE " + selected_values("borough", boroughs)
    return read_query(sql + " AND status IS NOT NULL ORDER BY status", boroughs)["status"].tolist()


def dashboard_filter(boroughs, statuses, start_hour, end_hour): # filter the dashboard requests by borough, status, and hour range, then return the SQL WHERE clause and the parameters for the query
    sql = (" WHERE " + selected_values("borough", boroughs)
           + " AND " + selected_values("status", statuses)
           + " AND hour BETWEEN ? AND ?")
    return sql, [*boroughs, *statuses, start_hour, end_hour]


# 先用总览页的三个条件筛选，再列出剩下的投诉类型，供用户继续选择。
def get_complaint_types(boroughs, statuses, start_hour, end_hour):
    where, params = dashboard_filter(boroughs, statuses, start_hour, end_hour)
    sql = "SELECT DISTINCT complaint_type FROM service_requests" + where
    return read_query(sql + " AND complaint_type IS NOT NULL ORDER BY complaint_type", params)["complaint_type"].tolist()


# 给总览页返回筛选后的投诉明细。选了具体投诉类型就再加一个条件，最后每一行仍然代表一条投诉。
def get_dashboard_requests(boroughs, statuses, start_hour, end_hour, complaint_type):
    where, params = dashboard_filter(boroughs, statuses, start_hour, end_hour)
    if complaint_type != "All":
        where += " AND complaint_type = ?"
        params.append(complaint_type)
    sql = """SELECT unique_key, created_date, closed_date, complaint_type, status, borough, latitude, longitude, hour, hours FROM service_requests"""
    return read_query(sql + where + " ORDER BY rowid", params)


# 计算整库的汇总数字，方便和筛选结果对照。这次查询不接收页面的筛选条件。
def get_dashboard_baseline():
    # total 是总投诉数，closed 是已结案数，timed 是已结案且耗时有效的条数。MIN 和 MAX 取最早、最晚的创建时间。
    totals = read_query("""
        SELECT COUNT(*) AS total, COUNT(CASE WHEN status = 'Closed' THEN 1 END) AS closed,
               COUNT(CASE WHEN status = 'Closed' AND hours >= 0 THEN 1 END) AS timed,
               MIN(created_date) AS first_created, MAX(created_date) AS last_created
        FROM service_requests
    """).iloc[0]
    # 排序后只取中间的值：奇数条取一条，偶数条取两条求平均。
    # 上面的汇总查询只返回一行，iloc[0] 取出这一行，之后就能按列名取值。
    timed = int(totals["timed"])
    median = None
    if timed:
        # OFFSET 表示跳过几行，LIMIT 表示取几行。例如 6 条耗时从小到大排好，跳过 2 条、取第 3 和第 4 条求平均。
        middle = read_query("""
            SELECT hours FROM service_requests WHERE status = 'Closed' AND hours >= 0
            ORDER BY hours LIMIT ? OFFSET ?
        """, (2 if timed % 2 == 0 else 1, (timed - 1) // 2))
        median = middle["hours"].mean()
    # 返回一个字典给页面用。rate 是结案百分比；没有有效耗时时，median 保持为 None。
    return {"total": totals["total"], "rate": totals["closed"] / totals["total"] * 100 if totals["total"] else 0, "median": median, "first_created": totals["first_created"], "last_created": totals["last_created"],}

# 在项目根目录运行 python app/db.py 时才导入样本；页面 import db 时只加载这些函数。
if __name__ == "__main__":
    import_sample()
