from datetime import date, timedelta
from models import room_classes


def pricing(room_type, check_in, check_out, guests, need_breakfast=False, completed_stays=0):
    room = room_classes[room_type]()
    Total_stay = (check_out - check_in).days

    room.Extra_guest_pay(max(0, guests - 2))
    extra_per_night = room.extra_pay

    room.breakfast("Yes" if need_breakfast else "No", guests)
    breakfast_per_night = room.breakfast_fee

    stay_discount = 0.10 if Total_stay >= 7 else 0
    loyalty_rate = 0.05 if completed_stays >= 3 else 0

    breakdown = []
    room_total = extra_total = breakfast_total = gst_total = 0

    for i in range(Total_stay):
        day = check_in + timedelta(days=i)
        tariff = room.Tariff(day.strftime("%A"))
        if tariff<=7500:
            gst_rate=0.12
        else:
            gst_rate=0.18

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