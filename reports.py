import csv
import sqlite3
from datetime import datetime, date, timedelta
from database import curr
from models import Room_Types
 
 
def report_date(text):
    while True:
        try:
            return datetime.strptime(input(text).strip(), "%d-%m-%Y").date()
        except ValueError:
            print("Use format DD-MM-YYYY")
 
 
def occupancy_report():
    start = report_date("Enter start date (DD-MM-YYYY): ")
    while True:
        end = report_date("Enter end date (DD-MM-YYYY): ")
        if end < start:
            print("End date cannot be before start date")
        elif (end - start).days + 1 > 366:
            print("Range cannot be more than 366 days")
        else:
            break
 
    try:
        curr.execute("select count(*) from rooms")
        total_rooms = curr.fetchone()[0]
        curr.execute("""select check_in, check_out from Booking
                        where status in ('CONFIRMED','CHECKED_IN','CHECKED_OUT')
                        and check_in <= ? and check_out > ?""",
                     (end.isoformat(), start.isoformat()))
        stays = [(date.fromisoformat(a), date.fromisoformat(b)) for a, b in curr.fetchall()]
    except sqlite3.Error:
        print("Database error. Could not build the report.")
        return
 
    if total_rooms == 0:
        print("No rooms loaded")
        return
 
    print(f"{'Night':<14}{'Occupied':>10}{'Total':>8}{'Occupancy':>12}")
    percents = []
    night = start
    while night <= end:
        occupied = sum(1 for cin, cout in stays if cin <= night < cout)
        pct = occupied / total_rooms * 100
        percents.append(pct)
        print(f"{night.strftime('%d-%m-%Y'):<14}{occupied:>10}{total_rooms:>8}{pct:>11.1f}%")
        night += timedelta(days=1)
 
    print(f"Average occupancy for {len(percents)} night(s): {sum(percents) / len(percents):.1f}%")
 
 
def revenue_report():
    try:
        curr.execute("""select r.room_type, count(*),
                        coalesce(sum(b.room_revenue), 0),
                        coalesce(sum(b.gst_amount), 0)
                        from Booking b join rooms r on r.room_no = b.room_no
                        where b.status='CHECKED_OUT'
                        group by r.room_type""")
        completed = {}
        for t, n, rev, gst in curr.fetchall():
            completed[t] = (n, rev, gst)
 
        curr.execute("""select r.room_type,
                        coalesce(sum(cast(b.amount_paid as real)- cast(b.refund_amount as real)), 0)
                        from Booking b join rooms r on r.room_no = b.room_no
                        where b.status='CANCELLED'
                        group by r.room_type""")
        kept = dict(curr.fetchall())
    except sqlite3.Error:
        print("Database error. Could not build the report.")
        return
 
    print(f"{'Room type':<12}{'Stays':>7}{'Room revenue':>16}{'GST collected':>16}{'Kept (cancel)':>16}")
    totals = [0, 0.0, 0.0, 0.0]
    for t in Room_Types:
        n, rev, gst = completed.get(t, (0, 0.0, 0.0))
        k = kept.get(t, 0.0)
        print(f"{t:<12}{n:>7}{rev:>16,.2f}{gst:>16,.2f}{k:>16,.2f}")
        totals[0] += n; totals[1] += rev; totals[2] += gst; totals[3] += k
    print(f"{'TOTAL':<12}{totals[0]:>7}{totals[1]:>16,.2f}{totals[2]:>16,.2f}{totals[3]:>16,.2f}")
 
 
def export_bookings():
    try:
        curr.execute("""select b.booking_id, g.guest_name, b.mobile_number, g.email, b.room_no,
                        b.check_in, b.check_out, b.num_guests, b.breakfast, b.status,
                        b.amount_paid, b.refund_amount
                        from Booking b left join Guests g on g.mobile_number = b.mobile_number
                        order by b.booking_id""")
        rows = curr.fetchall()
    except sqlite3.Error:
        print("Database error. Could not export the bookings.")
        return
 
    with open("bookings_export.csv", "w") as export_file:
        writer = csv.writer(export_file)
        writer.writerow(["booking_id","guest_name","mobile_number","email","room_no","check_in",
                         "check_out","num_guests","breakfast","status","amount_paid","refund_amount"])
        for r in rows:
            writer.writerow(["BK%04d" % r[0]] + list(r[1:]))
    print(f"{len(rows)} booking(s) exported to bookings_export.csv")
 
