from database import conn, load_rooms
from menu import menu
 
load_rooms()
menu()
conn.close()