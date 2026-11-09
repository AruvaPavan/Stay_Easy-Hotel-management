import csv

import sqlite3
from models import room_classes
from menu import Room_Types

conn=sqlite3.connect("stayeasy.db")
conn.execute("PRAGMA foreign_keys=ON")
curr=conn.cursor()
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
                    status text not null check(status in ('CONFIRMED','CHECKED_IN','CHECKED_OUT','CANCELLED')),
                    amount_paid text not null,
                    refund_amount text not null default 0,
                    availability text,
                    prior_stays integer not null default 0,
                    room_revenue real not null default 0,
                    gst_amount real not null default 0
                    
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
 
 
def load_rooms():
    app_log=[]
    seen_rooms=[]
    with open("rooms.csv","r") as file:
        reader=csv.reader(file)
        for line_no, row in enumerate(reader):
            if line_no==0:
                continue
 
            if len(row)!=3:
                app_log.append(f"Line {line_no}: expected 3 columns")
                continue
 
            room_no, r_type, floor = row
            r_type = r_type.strip().capitalize()
            valid=True
            try:
                room_no = int(room_no)
                if room_no<=0:
                    valid=False
                    app_log.append(f"Line {line_no}: room number {room_no} is invalid")
            except ValueError:
                valid=False
                app_log.append(f"Line {line_no}: room number {room_no} is not digit")
 
            if r_type not in Room_Types:
                app_log.append(f"Line {line_no}: unknown room type {r_type}")
                valid=False
 
            try:
                floor = int(floor)
            except ValueError:
                app_log.append(f"Line {line_no}: floor {floor} is not digit")
                valid=False
            if floor not in floors:
                app_log.append(f"Line {line_no}: floor {floor} is invalid")
                valid=False
 
            if valid and room_no in seen_rooms:
                app_log.append(f"Line {line_no}: duplicate room number {room_no}")
                valid=False
 
            if not valid:
                continue
            seen_rooms.append(room_no)
 
            no_ofmembers=room_classes[r_type].max_guest
 
            curr.execute("""insert or ignore into rooms(room_no,room_type,floor,max_people,availability) values(?,?,?,?,?)
                            """,(room_no,r_type,floor,no_ofmembers,'True'))
            conn.commit()
    with open("app.log","w") as log_file:
        for line in app_log:
            log_file.write(line+"\n")
 
