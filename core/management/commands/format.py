from collections import Counter
import re
from core.models import Customer

phones = []

for c in Customer.objects.all():
    phone = re.sub(r"\D", "", c.phone)

    if phone.startswith("1") and len(phone) == 11:
        phone = phone[1:]

    if len(phone) == 10:
        phone = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"

    phones.append(phone)

duplicates = [p for p, count in Counter(phones).items() if count > 1]

print(duplicates)