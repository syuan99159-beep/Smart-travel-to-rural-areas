from datetime import datetime, timedelta


def parse_hhmm(value):
    return datetime.strptime(value, "%H:%M")


def format_hhmm(value):
    return value.strftime("%H:%M")


def add_minutes(value, minutes):
    return value + timedelta(minutes=minutes)

