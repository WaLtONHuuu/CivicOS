# CivicOS SQLite update

Copy the app folder into your CivicOS project. The existing sample CSV is needed.

## Run it

From the project folder:

    py -m pip install -r requirements.txt
    py app/db.py
    py -m streamlit run app/streamlit_app.py

Run the import again to check that it adds zero duplicate rows.

## Files

- app/db.py: CSV import and database queries.
- app/ui_helpers.py: database messages and the two date controls.
- app/streamlit_app.py: home page.
- app/pages/1_Dashboard.py: statistics and charts.
- app/pages/2_Explorer.py: filtered map.

## Changes

- Both pages have start and end dates. They open on the last available day.
- Dashboard comparisons use all requests within the chosen dates.
- Trend charts can group by hour or day and can be downloaded.
- Hourly charts keep each date separate.
- The original partial sample can include or hide its last hour.
- Status counts and coordinate coverage are available below the tabs.
- Raw data supports request ID search. The table shows at most 1,000 rows.
- Raw CSV download includes all rows matching the current filters and ID search.
- Map shows matching requests, valid coordinates, and displayed point counts.
- Map point limit can be adjusted. It shows the earliest matching records.
- Displayed map points can be downloaded.
- The 3D chart samples points with a fixed seed when above the chosen limit.
- Invalid coordinates become NULL during import.
- If an import fails, its new rows are rolled back.
- Duplicate request IDs are skipped. Existing records are not refreshed by re-importing.
- Database reads use a read-only connection.

## More data

Import another CSV with the same eight source fields:

    py app/db.py "data/sample/more_requests.csv"

Create a separate database:

    py app/db.py "data/sample/year_requests.csv" --output "data/processed/civicos_year.db"

Select that database in PowerShell before starting Streamlit:

    $env:CIVICOS_DB_PATH = (Resolve-Path "data/processed/civicos_year.db").Path
    py -m streamlit run app/streamlit_app.py

Use the default database again:

    Remove-Item Env:CIVICOS_DB_PATH -ErrorAction SilentlyContinue

Restart Streamlit after changing the environment variable.

## Current limits

The supplied project sample only covers part of October 1, 2026.
This package contains code. Additional dates require importing additional data.
Observed start and end timestamps do not prove that a data source covers every day completely.
Dashboard still loads filtered details for its six views. Very large date ranges may use a lot of memory.
Map point limits apply only to the plotted points; displayed counts cover all matches.
The month/year data download and Docker packaging are still separate work.

## Checks performed

Sample totals, Brooklyn totals, and Brooklyn APPLIANCE totals match the original CSV.
Duplicate import, empty filters, date boundaries, invalid coordinates, failed-import rollback,
and missing database paths were checked.
Both page scripts and their default Plotly figures ran without errors in bare mode.
Browser interactions have not been fully verified. Streamlit AppTest could not initialize
its local event loop in the test environment.
