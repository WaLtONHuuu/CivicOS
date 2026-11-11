import csv
import turtle

csv_path = "data/sample/nyc311_2026-10_first10000.csv"
points = []
total = 0

with open(csv_path, "r", newline="") as file:
    for row in csv.DictReader(file):
        total += 1
        if row["longitude"] and row["latitude"]:
            longitude = float(row["longitude"])
            latitude = float(row["latitude"])
            if -180 <= longitude <= 180 and -90 <= latitude <= 90:
                points.append((longitude, latitude))

print(f"Requests read: {total:,}")
print(f"Requests with coordinates: {len(points):,}")

screen = turtle.Screen()
screen.setup(width=760, height=760)
screen.title("CivicOS | NYC 311 requests | October 1, 2026 (partial day)")
screen.tracer(0)
screen.setworldcoordinates(-74.28, 40.48, -73.68, 40.94)

pen = turtle.Turtle(visible=False)
pen.penup()
for longitude, latitude in points:
    pen.goto(longitude, latitude)
    pen.dot(3, "#FF0000")

screen.update()
screen.mainloop()
