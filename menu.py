import os
import sqlite3
from datetime import datetime, date, timedelta
from exceptions import room_unavailable,invalid_date,invaild_status_change,booking_not_found
from database import conn, curr, Search_room_available
from models import  room_classes
from pricing import pricing, refund_amount
from reports import occupancy_report, revenue_report, export_bookings
 
Room_Types=["Standard","Deluxe","Suite"]
def all_date(text,limit=True):
    while True:
        try:
            entered= datetime.strptime(input(text).strip(), "%d-%m-%Y").date()
        except ValueError:
            print("Use format DD-MM-YYYY")
            continue 
        today=date.today()
        max_date=today+timedelta(days=180)
        if entered<today:
            print("Date must be today or in future")
            continue 
        if limit and entered >max_date:
            print(f"connot book for after 6 months")
            continue
        return entered
 
    
def stay_dates():
    check_in = all_date("Enter check in on (DD-MM-YYYY): ")
    while True:
        check_out = all_date("Enter check out on (DD-MM-YYYY): ", limit=False)
        if check_out <= check_in:
            print("Check out must be greater than check in")
        elif (check_out - check_in).days > 30:
            print("Stay cannot be more than 30 nights")
        else:
            return check_in, check_out
 
 
def room_type():
    while True:
        room_type = input("Enter Room Type [Standard,Deluxe,Suite]: ").strip().capitalize()
        if room_type in Room_Types:
            return room_type
        print("only enter [Standard,Deluxe,Suite]")
 
 
def no_of_people():
    while True:
        try:
            n = int(input("Enter number of people (1 to 4): "))
            if 1 <= n <= 4:
                return n
            print("Cannot be greater than 4 or less than 1")
        except ValueError:
            print("Integers only")
 
 
def show_alternatives(room_type_asked,people,check_in,check_out):
    found=False
    for t in Room_Types:
        if t!=room_type_asked:
            rows=Search_room_available(t,people,check_in,check_out)
            if rows:
                print(t,"rooms available:")
                for r in rows:
                    print("Room",r[0])
                found=True
    if not found:
        print("No other room type is available for those dates")
 
def search_rooms():
    check_in, check_out = stay_dates()
    rtype = room_type()
    people = no_of_people()
    rows = Search_room_available(rtype, people, check_in, check_out)
    if rows:
        print(f"\nAvailable {rtype} rooms:")
        for r in rows:
            print(f"Room {r[0]} ({r[1]}) max guests {r[2]}")
    else:
        print(f"No {rtype} room is available for those dates for {people} guest(s).")
        show_alternatives(rtype, people, check_in, check_out)
 
 
def booking_id(text):
    text = text.strip().upper()
    if text.startswith("BK"):
        text = text[2:]
    if not text.isdigit():
        raise booking_not_found("Invalid booking ID")
    return int(text)
 
def create_booking():
    mobile_number=input("Enter Mobile number")
    while True:
        if not mobile_number.startswith(("9","8","7","6")) or len(mobile_number)!=10 or not mobile_number.isdigit():
            print("Wrong mobile number")
            mobile_number=input("Enter Mobile number")
        else:
            break
    
    while True:
        name=input("Enter Guest name: ").strip()
        if name=="":
            print("cant be empty")
        else:
            break
 
    while True:
        Email=input("Enter email ID: ").strip()
        if Email=="":
            print("cannot be empty")
            continue
        if Email.count("@")!=1 or " " in Email or "." not in Email.split("@")[-1]:
            print("Its not in email format")
        else:
            break
 
    check_in, check_out = stay_dates()
    chosen_type = room_type()
    room = room_classes[chosen_type]()
    number_of_people = no_of_people()
    
    rows = []
    if number_of_people <= room.max_guest:
        rows = Search_room_available(chosen_type, number_of_people, check_in, check_out)
    if not rows:
        if number_of_people > room.max_guest:
            print(f"{chosen_type} room allows only {room.max_guest} guests.")
        else:
            print(f"No {chosen_type} room is available for those dates.")
        show_alternatives(chosen_type, number_of_people, check_in, check_out)
        raise room_unavailable("Booking not created")
    room_no = rows[0][0]
 
    breakfast = False
    if room.breakfast_optional:
        breakfast = input("Breakfast (Rs.350 per guest per night)? yes/no: ").strip().lower() in ("y", "yes")
 
    curr.execute("select count(*) from Booking where mobile_number=? and status='CHECKED_OUT'",
                 (mobile_number,))
    prior_stays = curr.fetchone()[0]
 
    bill = pricing(chosen_type, check_in, check_out, number_of_people, breakfast, prior_stays)
    print(f"\nRoom {room_no} ({chosen_type}), {bill['nights']} night(s)")
    print(f"Room charges: Rs.{bill['room_charges']}")
    print(f"Extra guests: Rs.{bill['extra_guest_charges']}")
    print(f"Breakfast: Rs.{bill['breakfast_charges']}")
    print(f"Discounts: Rs.{bill['stay_discount'] + bill['loyalty_discount']:,.2f}")
    print(f"GST: Rs.{bill['gst']}")
    print(f"TOTAL TO PAY : Rs.{bill['total']}")
    if input("Confirm and pay? (yes/no): ").strip().lower() not in ("y", "yes"):
        print("Booking cancelled by user")
        return
 
    try:
        curr.execute("""insert into Guests(guest_name,mobile_number,email,no_of_people) values(?,?,?,?)
                        on conflict(mobile_number) do update set
                        guest_name=excluded.guest_name, email=excluded.email,
                        no_of_people=excluded.no_of_people""",
                     (name, mobile_number, Email, number_of_people))
        curr.execute("""insert into Booking(mobile_number,room_no,check_in,check_out,num_guests,
                        breakfast,status,amount_paid,refund_amount,prior_stays,room_revenue,gst_amount)
                        values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (mobile_number, room_no, check_in.isoformat(), check_out.isoformat(),
                      number_of_people, int(breakfast), "CONFIRMED", bill["total"], 0, prior_stays,
                      round(bill["total"] - bill["gst"], 2), bill["gst"]))
        booking_id = curr.lastrowid
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    print(f"Booking confirmed! Booking ID: BK{booking_id:04d}, Room {room_no}")
 
 
def check_in():
    try:
        bid = booking_id(input("Enter Booking ID (e.g. BK0001): "))
 
        curr.execute("select status, check_in, room_no from Booking where booking_id=?",
                     (bid,))
        row = curr.fetchone()
        if row is None:
            raise booking_not_found(f"No booking found with ID BK{bid:04d}")
 
        status, check_in_date, room_no = row
        if status != "CONFIRMED":
            raise invaild_status_change(f"Cannot check in a booking that is {status}")
 
        if date.fromisoformat(check_in_date) != date.today():
            raise invalid_date(
                f"Check-in is allowed only on the check-in date ({check_in_date})")
 
        curr.execute("""update Booking set status='CHECKED_IN'
                        where booking_id=? and status='CONFIRMED'""", (bid,))
        conn.commit()
    except (booking_not_found, invaild_status_change, invalid_date) as e:
        print(e)
        return
    except sqlite3.Error:
        conn.rollback()
        print("Database error. Nothing was changed.")
        return
 
    print(f"Booking BK{bid:04d} checked in. Room {room_no}.")
 
 
def check_out():
    try:
        bid = booking_id(input("Enter Booking ID (e.g. BK0001): "))
 
        curr.execute("""select b.booking_id, g.guest_name, b.mobile_number, g.email,
                        b.room_no, r.room_type, b.check_in, b.check_out,
                        b.num_guests, b.breakfast, b.status, b.prior_stays
                        from Booking b
                        join Guests g on g.mobile_number = b.mobile_number
                        join rooms r on r.room_no = b.room_no
                        where b.booking_id=?""", (bid,))
        row = curr.fetchone()
        if row is None:
            raise booking_not_found(f"No booking found with ID BK{bid:04d}")
        (bid, name, mobile, email, room_no, rtype, cin, cout, guests, breakfast, status, prior_stays) = row
        if status != "CHECKED_IN":
            raise invaild_status_change(f"Cannot check out a booking that is {status}")
        bill = pricing(rtype, date.fromisoformat(cin), date.fromisoformat(cout), guests, bool(breakfast), prior_stays)
        curr.execute("""update Booking set status='CHECKED_OUT'
                        where booking_id=? and status='CHECKED_IN'""", (bid,))
        os.makedirs("invoices", exist_ok=True)
        lines = []
        lines.append("STAYEASY HOTEL - INVOICE")
        lines.append(f"Booking ID : BK{bid:04d}")
        lines.append(f"Guest: {name}")
        lines.append(f"Mobile: {mobile}")
        lines.append(f"Email: {email}")
        lines.append(f"Room: {room_no} ({rtype})")
        lines.append(f"Check-in: {cin}")
        lines.append(f"Check-out: {cout} ({bill['nights']} night(s))")
        lines.append(f"Guests: {guests}")
        lines.append("")
        lines.append(f"{'Date':<12}{'Day':<11}{'Tariff':>10}{'Extra guest':>13}{'Breakfast':>11}{'GST rate':>10}")
        for night in bill["breakdown"]:
            lines.append(f"{night['date']:<12}{night['day']:<11}{night['tariff']:>10,.2f}{night['extra_guest']:>13,.2f}{night['breakfast']:>11,.2f}{night['gst_rate']*100:>9.0f}%")
        lines.append("")
        lines.append(f"Room charges: Rs.{bill['room_charges']:,.2f}")
        lines.append(f"Extra guest : Rs.{bill['extra_guest_charges']:,.2f}")
        lines.append(f"Breakfast charges: Rs.{bill['breakfast_charges']:,.2f}")
        lines.append(f"Stay discount: Rs.{bill['stay_discount']:,.2f}")
        lines.append(f"Loyalty discount: Rs.{bill['loyalty_discount']:,.2f}")
        lines.append(f"GST: Rs.{bill['gst']:,.2f}")
        lines.append(f"TOTAL AMOUNT: Rs.{bill['total']:,.2f}")
        with open(f"invoices/BK{bid:04d}.txt", "w", encoding="utf-8") as invoice_file:
            for line in lines:
                invoice_file.write(line + "\n")
 
        conn.commit()
    except (booking_not_found, invaild_status_change) as e:
        print(e)
        return
    except (sqlite3.Error, OSError):
        conn.rollback()
        print("Error. Nothing was changed.")
        return
 
    print(f"{'Booking ID':>12}{'Name':>12}{'mobile number':>18}{'check-In':>18}{'check-out':>18}{'Charge per night':>18}{'extra Charges':>15}{'Discount':>10}{'GST':>10}{'Total Amount':>14}")
    print(f"{'BK%04d' % bid:>12}{name:>12}{mobile:>18}{cin:>18}{cout:>18}{bill['room_charges'] / bill['nights']:>18,.2f}{bill['extra_guest_charges'] + bill['breakfast_charges']:>15,.2f}{bill['stay_discount'] + bill['loyalty_discount']:>10,.2f}{bill['gst']:>10,.2f}{bill['total']:>14,.2f}")
    print(f"Invoice saved in invoices/BK{bid:04d}.txt")
 
 
def cancel_booking():
    try:
        booking_ids = booking_id(input("Enter Booking ID (e.g. BK0001):"))
 
        curr.execute("select status, check_in, amount_paid from Booking where booking_id=?",
                     (booking_ids,))
        row = curr.fetchone()
        if row is None:
            raise booking_not_found(f"No booking found with ID BK{booking_ids:04d}")
 
        status, check_in, amount_paid = row
        if status != "CONFIRMED":
            raise invaild_status_change(f"Cannot cancel a booking that is {status}")
 
        refund = refund_amount(amount_paid, date.fromisoformat(check_in))
 
        curr.execute("""update Booking set status='CANCELLED', refund_amount=?
                        where booking_id=? and status='CONFIRMED'""",
                     (refund, booking_ids))
        conn.commit()
    except (booking_not_found, invaild_status_change) as e:
        print(e)
        return
    except sqlite3.Error:
        conn.rollback()
        print("Database error. Nothing was changed.")
        return
 
    print(f"Booking BK{booking_ids:04d} cancelled.")
    print(f"Amount paid : Rs.{float(amount_paid)}")
    print(f"Refund: Rs.{refund}")
 
def view_booking():
    try:
        bid =booking_id(input("Enter Booking ID (e.g. BK0001): "))
 
        curr.execute("""select b.booking_id, g.guest_name, b.mobile_number, g.email,
                        b.room_no, r.room_type, b.check_in, b.check_out,
                        b.num_guests, b.breakfast, b.status,
                        b.amount_paid, b.refund_amount
                        from Booking b
                        join Guests g on g.mobile_number = b.mobile_number
                        join rooms r on r.room_no = b.room_no
                        where b.booking_id=?""", (bid))
        row = curr.fetchone()
        if row is None:
            raise booking_not_found(f"No booking found with ID BK{bid:04d}")
    except booking_not_found as e:
        print(e)
        return
    except sqlite3.Error:
        print("Database error. Could not read the booking.")
        return
 
    (bid, name, mobile, email, room_no, rtype, cin, cout, guests, breakfast, status, paid, refund) = row
 
    nights = (date.fromisoformat(cout) - date.fromisoformat(cin)).days
    print(f"Booking ID: BK{bid:04d}")
    print(f"Status : {status}")
    print(f"Guest :{name}")
    print(f"Mobile: {mobile}")
    print(f"Email:{email}")
    print(f"Room: {room_no} ({rtype})")
    print(f"Check-in: {cin}")
    print(f"Check-out: {cout} ({nights} night(s))")
    print(f"Guests: {guests}")
    print(f"Breakfast: {'Yes' if breakfast else 'No'}")
    print(f"Amount paid: Rs.{float(paid)}")
    print(f"Refund: Rs.{float(refund)}")
 
 
def guest_stay_history():
    mobile = input("Enter mobile number:").strip()
    if not (mobile.isdigit() and len(mobile) == 10 and mobile[0] in "6789"):
        print("Invalid mobile number")
        return
    try:
        curr.execute("select guest_name, email from Guests where mobile_number=?", (mobile,))
        guest = curr.fetchone()
        if guest is None:
            print("No guest found with that mobile number")
            return
        curr.execute("""select booking_id, room_no, check_in, check_out,status, amount_paid, refund_amount
                        from Booking where mobile_number=?
                        order by check_in desc, booking_id desc""", (mobile,))
        rows = curr.fetchall()
    except sqlite3.Error:
        print("Database error. Could not read the history.")
        return
    print(f"Guest:{guest[0]} {guest[1]} {mobile}")
    if not rows:
        print("No bookings yet")
        return
 
    print(f"\n{'Booking':<9}{'Room':<6}{'Check-in':<12}{'Check-out':<12}{'Status':<13}{'Paid':>12}{'Refund':>12}")
    for bid, room_no, cin, cout, status, paid, refund in rows:
        print(f"{'BK%04d' % bid:<9}{room_no:<6}{cin:<12}{cout:<12}{status:<13}{float(paid):>12}{float(refund):>12}")
    completed = sum(1 for r in rows if r[4] == "CHECKED_OUT")
    print(f"Total bookings: {len(rows)}Completed stays: {completed}")
 
 
def menu():
    while True:
        print("""1. Search room availability
2. Create booking
3. Check in
4. Check out (generate invoice)
5. Cancel booking
6. View booking details
7. Guest stay history (by mobile number)
8. Occupancy report (for a date range)
9. Revenue report (by room type)
10. Export all bookings to CSV
11. Exit""")
        choice=input("Enter a number from above (1-11): ")
        try:
            if choice=="1":
                search_rooms()
            elif choice=="2":
                create_booking()
            elif choice=="3":
                check_in()
            elif choice=="4":
                check_out()
            elif choice=="5":
                cancel_booking()
            elif choice=="6":
                view_booking()
            elif choice=="7":
                guest_stay_history()
            elif choice=="8":
                occupancy_report()
            elif choice=="9":
                revenue_report()
            elif choice=="10":
                export_bookings()
            elif choice=="11":
                break
            else:
                print("enter number between 1 to 11")
        except (room_unavailable, invalid_date, invaild_status_change, booking_not_found) as e:
            print(e)
        except Exception:
            conn.rollback()
            print("Something went wrong. Nothing was changed.")
 
