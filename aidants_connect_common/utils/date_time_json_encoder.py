import json
from datetime import date, datetime, time, timedelta


class DateTimeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return (datetime.min + obj).time().isoformat()

        return super(DateTimeJsonEncoder, self).default(obj)
