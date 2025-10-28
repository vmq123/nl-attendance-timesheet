import frappe
from frappe.utils import today
from datetime import datetime, timedelta

def before_save_hook(doc, method=None):
    if doc.doctype != "Shift Type":
        return
    """
    Calculates the duration in hours between two timestamps.

    Args:
        start_timestamp_str (str): The start timestamp as a string.
        end_timestamp_str (str): The end timestamp as a string.
        date_format (str): The format of the timestamp strings.
                           Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        float: The duration in hours.
        4Oct: TODO: unit test
    """
    start_timestamp_str = f"{today()} {doc.start_time}"
    end_timestamp_str = f"{today()} {doc.end_time}"
    date_format="%Y-%m-%d %H:%M:%S"
    try:
        start_dt = datetime.strptime(start_timestamp_str, date_format)
        end_dt = datetime.strptime(end_timestamp_str, date_format)
        if end_dt < start_dt:
            end_dt = end_dt + timedelta(days=1)
        time_difference = end_dt - start_dt
        duration_in_hours = time_difference.total_seconds() / 3600
        doc.total_shift_hours = duration_in_hours
    except ValueError as e:
        frappe.log_error(f"Error parsing date: {e}. Please ensure the date format matches the input strings.")