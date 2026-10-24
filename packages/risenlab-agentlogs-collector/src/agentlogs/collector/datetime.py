import datetime as dt

def format_timedelta(td: dt.timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def get_utc_datetime(
    day: int, 
    month: int, 
    year: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0
) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, second, tzinfo=dt.timezone.utc)

def get_utc_min() -> dt.datetime:
    return dt.datetime.min.replace(tzinfo=dt.timezone.utc)

def get_utc_max() -> dt.datetime:
    return dt.datetime.max.replace(tzinfo=dt.timezone.utc)

def get_utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def format_utc_datetime(datetime: dt.datetime) -> str:
    if datetime.tzinfo != dt.timezone.utc:
        raise ValueError("datetime must be in UTC")
    
    return datetime.strftime("%Y-%m-%d %H:%M:%S")

def parse_utc_datetime(datetime_str: str) -> dt.datetime:
    return dt.datetime.fromisoformat(datetime_str).replace(tzinfo=dt.timezone.utc)