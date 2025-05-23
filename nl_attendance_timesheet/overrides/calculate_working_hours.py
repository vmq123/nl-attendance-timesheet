from datetime import datetime
import frappe


def time_diff_in_hours(start, end):
    """Calculate time difference in hours rounded to 2 decimals"""
    return round(float((end - start).total_seconds()) / 3600, 2)


def calculate_working_hours(doc, method=None):
    """Calculate and update working hours in Attendance record"""
    if not doc.calculate_working_hours:
        frappe.log_error("Working hours calculation disabled", doc.name)
        return

    try:
        in_time = datetime.strptime(doc.in_time, "%Y-%m-%d %H:%M:%S")
        out_time = datetime.strptime(doc.out_time, "%Y-%m-%d %H:%M:%S")

        if None in (in_time, out_time):
            frappe.log_error("Missing time data", doc.name)
            return

        if out_time < in_time:
            frappe.log_error("Out time cannot be before in time", doc.name)
            return
        total_hours = time_diff_in_hours(in_time, out_time)

        doc.working_hours = total_hours

    except Exception as e:
        frappe.log_error(f"Error calculating working hours for {doc.name}: {str(e)}")
