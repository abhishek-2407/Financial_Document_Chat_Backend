from datetime import datetime
from zoneinfo import ZoneInfo

now_india = datetime.now(ZoneInfo("Asia/Kolkata"))
formatted_date = now_india.strftime("%d-%b-%Y")
print(formatted_date)

