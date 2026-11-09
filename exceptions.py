class StayEasyError(Exception):
    pass

class room_unavailable(StayEasyError):
    pass 
class invalid_date(StayEasyError):
    pass 
class invaild_status_change(StayEasyError):
    pass
class booking_not_found(StayEasyError):
    pass 