from abc import ABC , abstractmethod
 
Room_Types=["Standard","Deluxe","Suite"]
floors=[1,2,3]
 
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
    breakfast_optional=True
    def Tariff(self,day):
        if day not in weekend:
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
        if day not in weekend:    
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
 
