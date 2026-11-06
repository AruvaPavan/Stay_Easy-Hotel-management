from abc import ABC , abstractmethod
import csv
import sqlite3
from exceptions import room_unavailable,invalid_date,invaild_status_change,booking_not_found
from datetime import datetime, date ,timedelta
conn=sqlite3.connect("stayeasy.db")
conn.execute("PRAGMA foreign_keys=ON")
curr=conn.cursor()
Room_Types=["Standard","Deluxe","Suite"]
floors=[1,2,3]
def create_database():
    curr.execute("""
                    create table if not exists rooms(
                    room_no numeric primary key,
                    room_type text not null check(room_type in ('Standard','Deluxe','Suite')),
                    floor numeric,
                    max_people numeric,
                    availability text check(availability in ('True','False')))""")
    curr.execute("""
                    create table if not exists Booking(
                    booking_id integer primary key AutoIncrement,
                    mobile_number numeric,
                    room_no numeric,
                    check_in text not null,
                    check_out text not null,
                    num_guests integer not null check(num_guests between 1 and 4),
                    breakfast integer not null default 0,
                    status text not null check(status in ('conformed','checked_in','check_out','cancelled')),
                    amount_paid text not null,
                    refund_amount text not null default 0,
                    availability text
                    
                    )""")
    curr.execute("""
                    create table if not exists Guests(
                    guest_name text not null ,
                    mobile_number numeric check(mobile_number GLOB '[6-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]') primary key,
                    email text not null,
                    no_of_people numeric not null check(no_of_people between 1 and 4))""")
    conn.commit()
create_database()

def load():
    curr.execute("Select * from rooms")
    for i in curr.fetchall():
        print(i)


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
    """Ask check-in and check-out (1 to 30 nights)"""
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



def Search_room_available(room_type,people,check_in,check_out):
    curr.execute("""select room_no, room_type, max_people from rooms r
                    where room_type=? and max_people>=?
                    and not exists(select 1 from Booking b
                                   where b.room_no=r.room_no
                                   and b.status in ('CONFIRMED','CHECKED_IN')
                                   and b.check_in < ? and b.check_out > ?)
                    order by room_no""",
                 (room_type, people, check_out.isoformat(), check_in.isoformat()))
    return curr.fetchall()
            
    



weekend=("Friday","Saturday")
class Room(ABC):
    base_price=0
    max_free_guests=2
    breakfast_optional=False
    max_guest=2
    @abstractmethod
    def Tariff(self,day):
        if day in weekend:
            return self.base_price*(1.2)
        else:
            return self.base_price
    @abstractmethod
    def Extra_guest_pay(self,extra_guests):
        pass 
    @abstractmethod
    def breakfast(self,option,no_of_people):
        pass 
    def totalPay(self):
        pass

class StandardRoom(Room):
    base_price=2500
    max_guest=2
    def Tariff(self,day):
        if day not in ("Friday" or "saturday"):
            return self.base_price
        else:
            return self.base_price*1.20
    def Extra_guest_pay(self, extra_guests):
        self.extra_pay=0 
    def breakfast(self,option,no_of_persons):
        if option=="Yes":
            self.breakfast_fee=350*no_of_persons
        else:
            self.breakfast_fee=0 

class DeluxeRoom(Room):
    base_price=4000
    max_guest=3
    def Tariff(self,day):
        if day not in ("Friday" or "saturday"):    
            return self.base_price
        else:
            return self.base_price*1.20
    def Extra_guest_pay(self,extra_guests):
        self.extra_pay=800*extra_guests
    def breakfast(self,option,no_of_persons):
        self.breakfast_fee=0  

class SuiteRoom(Room):
    base_price=7500
    max_guest=4
    def Tariff(self,day):
        if day in weekend:    
            return self.base_price*1.20
        else:
            return self.base_price
    def Extra_guest_pay(self,extra_guest):
        self.extra_pay=800*extra_guest 
    def breakfast(self,option,no_of_persons):
        self.breakfast_fee=0 

room_classes={"Standard":StandardRoom,"Deluxe":DeluxeRoom,"Suite":SuiteRoom}



def pricing(room_type, check_in, check_out, guests, breakfast=False, completed_stays=0):
    room = room_classes[room_type]()
    Total_stay = (check_out - check_in).days

    room.Extra_guest_pay(max(0, guests - 2))
    extra_per_night = room.extra_pay

    room.breakfast("Yes" if breakfast else "No", guests)
    breakfast_per_night = room.breakfast_fee

    stay_discount = 0.10 if Total_stay >= 7 else 0
    loyalty_rate = 0.05 if completed_stays >= 3 else 0

    breakdown = []
    room_total = extra_total = breakfast_total = gst_total = 0

    for i in range(Total_stay):
        day = check_in + timedelta(days=i)
        tariff = room.base_price * 1.2 if day.strftime("%A") in weekend else room.base_price
        gst_rate = 0.12 if tariff <= 7500 else 0.18

        night_room_after_disc = tariff * (1 - stay_discount - loyalty_rate)
        taxable = night_room_after_disc + extra_per_night + breakfast_per_night
        gst = taxable * gst_rate

        breakdown.append({
            "date": day.strftime("%d-%m-%Y"),
            "day": day.strftime("%A"),
            "tariff": round(tariff, 2),
            "extra_guest": extra_per_night,
            "breakfast": breakfast_per_night,
            "gst_rate": gst_rate,
        })
        room_total += tariff
        extra_total += extra_per_night
        breakfast_total += breakfast_per_night
        gst_total += gst

    stay_discount = round(room_total * stay_discount, 2)
    loyalty_discount = round(room_total * loyalty_rate, 2)
    gst_total = round(gst_total, 2)
    total = round(room_total - stay_discount - loyalty_discount
                  + extra_total + breakfast_total + gst_total, 2)

    return {
        "nights": Total_stay,
        "breakdown": breakdown,
        "room_charges": round(room_total, 2),
        "extra_guest_charges": extra_total,
        "breakfast_charges": breakfast_total,
        "stay_discount": stay_discount,
        "loyalty_discount": loyalty_discount,
        "gst": gst_total,
        "total": total,
    }

def booking_id(text):
    """Accepts 'BK0001', 'bk0001' or '1'."""
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
        if not "@" in Email:
            print("Its not in email format")
        else:
            break

    check_in, check_out = stay_dates()
    room_type = room_type()
    room = room_classes[room_type]()
    number_of_people = no_of_people()
    
    rows = []
    if number_of_people <= room.max_guests:
        rows = Search_room_available(room_type, number_of_people, check_in, check_out)
    if not rows:
        if number_of_people > room.max_guests:
            print(f"{room_type} room allows only {room.max_guests} guests.")
        # else:
        #     print(f"No {room_type} room is available for those dates.")
        # show_alternatives(room_type, number_of_people, check_in, check_out)
        # raise room_unavailable("Booking not created")
    room_no = rows[0]["room_no"]
 
    breakfast = False
    if room.breakfast_optional:
        breakfast = input("Breakfast (Rs.350 per guest per night)? yes/no: ").strip().lower() in ("y", "yes")
 
    curr.execute("select count(*) from Booking where mobile_number=? and status='CHECKED_OUT'",
                 (mobile_number,))
    prior_stays = curr.fetchone()[0]
 
    bill = pricing(room_type, check_in, check_out, number_of_people, breakfast, prior_stays)
    print(f"\nRoom {room_no} ({room_type}), {bill['nights']} night(s)")
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
                        breakfast,status,amount_paid,refund_amount,prior_stays)
                        values(?,?,?,?,?,?,?,?,?,?)""",
                     (mobile_number, room_no, check_in.isoformat(), check_out.isoformat(),
                      number_of_people, int(breakfast), "CONFIRMED", bill["total"], 0, prior_stays))
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
    print(f"{'Booking ID':>12}{'Name':>12}{'mobile number':>18}{'check-In':>18}{'check-out':>18}{'Charge per night':>18}{'extra Charges':>15}{'Discount':>10}{'GST':>10}{'Total Amount':>14}")
    b = create_booking(booking_id())
    bill = pricing(b["room_type"], date.fromisoformat(b["check_in"]), date.fromisoformat(b["check_out"]), b["num_guests"], bool(b["breakfast"]), b["prior_stays"])
    print(f"{'BK%04d' % b['booking_id']:>12}{b['guest_name']:>12}{b['mobile_number']:>18}{b['check_in']:>18}{b['check_out']:>18}{bill['room_charges'] / bill['nights']:>18,.2f}{bill['extra_guest_charges'] + bill['breakfast_charges']:>15,.2f}{bill['stay_discount'] + bill['loyalty_discount']:>10,.2f}{bill['gst']:>10,.2f}{bill['total']:>14,.2f}")


def refund_amount(amount_paid, check_in, today=None):
    today = today or date.today()
    days_before = (check_in - today).days
    if days_before >= 7:
        rate = 1.0
    elif days_before >= 2:
        rate = 0.5
    else:
        rate = 0.0
    return round(float(amount_paid) * rate, 2)

def cancel_booking():
    try:
        booking_ids = booking_id(input("Enter Booking ID (e.g. BK0001):"))

        curr.execute("select status, check_in, amount_paid from Booking where booking_id=?",
                     (booking_ids,))
        row = curr.fetchone()
        if row is None:
            raise booking_not_found(f"No booking found with ID BK{booking_id:04d}")

        status, check_in, amount_paid = row
        if status != "CONFIRMED":
            raise invaild_status_change(f"Cannot cancel a booking that is {status}")

        refund = refund_amount(amount_paid, date.fromisoformat(check_in))

        curr.execute("""update Booking set status='CANCELLED', refund_amount=?
                        where booking_id=? and status='CONFIRMED'""",
                     (refund, booking_id))
        conn.commit()
    except (booking_not_found, invaild_status_change) as e:
        print(e)
        return
    except sqlite3.Error:
        conn.rollback()
        print("Database error. Nothing was changed.")
        return

    print(f"Booking BK{booking_id:04d} cancelled.")
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
                        where b.booking_id=?""", (bid,))
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
    print(f"\nBooking ID: BK{bid:04d}")
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



#csvfile
app_log=[]
with open("rooms.csv","r") as file:
    reader=csv.reader(file)
    # print(reader)
    for line_no, row in enumerate(reader):
        if line_no==0:
            continue

        if len(row)!=3:
            app_log.append("foeleds empty")
            continue

        room_no, room_type, floor = row
        # print(room_no, room_type, floor)
        valid=True
        no_ofmembers=2 
        try:
            room_no = int(room_no)
        except ValueError:
            valid=False
            app_log.append(f"{line_no} {room_no} is not digit")

        if room_type.capitalize() not in Room_Types:
            app_log.append(f"{line_no} {room_type}")
            valid=False

        try:
            floor = int(floor)
        except ValueError:
            app_log.append(f"{line_no} {floor} is not digit")
            valid=False
        if floor not in floors:
            app_log.append(f"{line_no} {floor}")
            valid=False

        if room_type=="Standard":
            no_ofmembers+=0
        elif room_type=="Deluxe":
            no_ofmembers+=1
        elif room_type=="Suite":
            no_ofmembers+=2

        if not valid:
            continue

        # print(room_no,room_type,floor,no_ofmembers)
        curr.execute("""insert or ignore into rooms(room_no,room_type,floor,max_people,availability) values(?,?,?,?,?)
                        """,(room_no,room_type,floor,no_ofmembers,'True'))
        conn.commit()
with open("app.log","w") as log_file:
    for line in app_log:
        log_file.write(line)



#functional_Menu

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
while True:
    choice=input("Enter a number from above (1-11): ")
    if choice=="1":
        Search_room_available() 
    elif choice=="2":
        create_booking()
    elif choice=="3":
        check_in()
        pass
    elif choice=="4":
        check_out()
    elif choice=="5":
        cancel_booking()
    elif choice=="6":
        view_booking()
    elif choice=="7":
        #guest_stay_history
        pass
    elif choice=="8":
        pass
    elif choice=="9":
        pass
    elif choice=="10":
        pass
    elif choice=="11":
        break
    else:
        print("enter number between 1 to 11")
