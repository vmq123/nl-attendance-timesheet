import frappe
from frappe import _
from datetime import datetime, timedelta

from ..controllers.get_employee_attendance import get_employee_attendance, get_employee_overtime_attendance
from ..controllers.generate_overtime_timesheets import generate_overtime_timesheets
from pypika import Criterion


def execute():
    start_date = "2025-04-01"
    end_date = "2025-04-30"

    process_attendance_after = start_date
    last_sync_of_checkin = end_date + " 23:59:00"

    # check_add_hour()
    # process_attendance(process_attendance_after,last_sync_of_checkin)
    # generate_overtime_timesheets(start_date,end_date)
    
    # add_attendance_data("HR-PRUN-2025-00017")
    add_incentive_data("HR-PRUN-2025-00017")
    # calculate_salary_slip("Sal Slip/HR-EMP-00005/00007")

def calculate_salary_slip(name):
    doc = frappe.get_doc("Salary Slip", name)
    # doc.hourly_rate = 30000
    # doc.save()
    doc.calculate_net_pay()

def add_incentive_data(payroll_entry):
    # doc = frappe.get_doc("Payroll Entry", payroll_entry)

    salary_slips = frappe.db.get_all('Salary Slip', filters = { 'payroll_entry': payroll_entry, 'docstatus': 0 })
    print(f"salary_slips: {salary_slips}")
    for entry in salary_slips:
        salary_slip = frappe.get_doc('Salary Slip', entry.get('name'))
        start_date, end_date=salary_slip.start_date, salary_slip.end_date
    
        sales_team = frappe.qb.DocType("Sales Team")
        sales_order = frappe.qb.DocType("Sales Order")
        sales_person = frappe.qb.DocType("Sales Person")
        salary_slip_qb = frappe.qb.DocType("Salary Slip")

        conditions = [sales_order.docstatus == 1, sales_order.transaction_date[start_date:end_date],
                    salary_slip_qb.incentive_based_salary == 1, salary_slip_qb.payroll_entry == payroll_entry, 
                    sales_team.parenttype == "Sales Order"]

        query = frappe.qb.from_(sales_team) \
            .left_join(sales_order) \
            .on(sales_team.parent == sales_order.name) \
            .left_join(sales_person) \
            .on(sales_team.sales_person == sales_person.sales_person_name) \
            .left_join(salary_slip_qb) \
            .on(salary_slip_qb.employee == sales_person.employee) \
            .select(
            sales_team.parent.as_("parent"),
            sales_team.allocated_percentage.as_("allocated_percentage"),
            sales_team.allocated_amount.as_("allocated_amount"),
            sales_team.commission_rate.as_("commission_rate"),
            sales_team.incentives.as_("incentives")
        ).where(Criterion.all(conditions))

        incentive_records = query.run(as_dict=True)
        incentives_total = 0

        for entry in incentive_records:
            print(f"entry: {entry}")
            salary_slip.append('incentive', {
                'sales_order': entry.get('parent'),
                'allocated_percentage': entry.get('allocated_percentage'),
                'allocated_amount': entry.get('allocated_amount'),
                'commission_rate': entry.get('commission_rate'),
                'incentives': entry.get('incentives')
            })
            incentives_total += entry.incentives
        salary_slip.incentives_total = incentives_total
        if salary_slip.incentive:
            salary_slip.save(ignore_permissions=True)
            frappe.db.commit()
    

def process_attendance(process_attendance_after,last_sync_of_checkin):
    format_string_1 = "%Y-%m-%d %H:%M:%S"
    format_string_2 = "%Y-%m-%d"

    shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
    for shift in shift_list:
        doc = frappe.get_doc("Shift Type", shift)
        
        doc.process_attendance_after = datetime.strptime(process_attendance_after, format_string_2)
        doc.last_sync_of_checkin = datetime.strptime(last_sync_of_checkin,format_string_1)
        doc.save(
            ignore_permissions=True, # ignore write permissions during insert
            ignore_version=True # do not create a version record
        )
        print(f"Shift_type: {doc}")
        doc.process_auto_attendance()
    
def add_attendance_data(payroll_entry):
    SETTINGS_DOCTYPE = 'Navari Custom Payroll Settings'

    maximum_monthly_hours = frappe.db.get_single_value(SETTINGS_DOCTYPE, 'maximum_monthly_hours')
    overtime_15 = frappe.db.get_single_value(SETTINGS_DOCTYPE, 'overtime_15_activity')
    overtime_20 = frappe.db.get_single_value(SETTINGS_DOCTYPE, 'overtime_20_activity')

    salary_slips = frappe.db.get_all('Salary Slip', filters = { 'payroll_entry': payroll_entry, 'docstatus': 0 })
    print(f"salary_slips: {salary_slips}")

    for entry in salary_slips:
        salary_slip = frappe.get_doc('Salary Slip', entry.get('name'))
        # TODO: get real duration from shift_type instead of 8
        maximum_monthly_hours = salary_slip.total_working_days * 8
        print(f"maximum_monthly_hours: {maximum_monthly_hours}")
        salary_slip.attendance = []
        salary_slip.regular_overtime = []
        salary_slip.holiday_overtime = []

        salary_slip.regular_working_hours = 0
        salary_slip.overtime_hours = 0
        salary_slip.holiday_hours = 0

        attendance = get_employee_attendance(salary_slip.get('employee'), salary_slip.get('start_date'), salary_slip.get('end_date'))
        # print(f"attendance: {attendance}")
        overtime_attendance = get_employee_overtime_attendance(salary_slip.get('employee'), salary_slip.get('start_date'), salary_slip.get('end_date'))
        # print(f"overtime_attendance: {overtime_attendance}")
        # holiday_dates = get_holiday_dates(salary_slip.get('employee'))
        holiday_dates = salary_slip.get_holidays_for_employee(salary_slip.start_date,salary_slip.end_date)
        # print(f"holiday_dates: {holiday_dates}")


        if attendance:
            for attendance_entry in attendance:
                print(f"attendance_entry: {attendance_entry}")
                if attendance_entry.get('attendance_date') not in (holiday_dates or []) and attendance_entry.get('working_hours') > 0:
                    billiable_hours = 0

                    if not attendance_entry.get('include_unpaid_breaks'):
                        billiable_hours = attendance_entry.get('payment_hours')
                    else:
                        if attendance_entry.get('working_hours') > attendance_entry.get('min_hours_to_include_a_break'):
                            billiable_hours = attendance_entry.get('working_hours') - (attendance_entry.get('unpaid_breaks_minutes') / 60)
                        else:
                            billiable_hours = attendance_entry.get('working_hours')

                    salary_slip.append('attendance', {
                        'attendance_date': attendance_entry.get('attendance_date'),
                        'hours_worked': attendance_entry.get('working_hours'),
                        'include_unpaid_breaks': attendance_entry.get('include_unpaid_breaks'),
                        'unpaid_breaks_minutes': attendance_entry.get('unpaid_breaks_minutes'),
                        'min_hours_to_include_a_break': attendance_entry.get('min_hours_to_include_a_break'),
                        'billiable_hours': billiable_hours
                    })

                    salary_slip.regular_working_hours += billiable_hours
        

        if overtime_attendance:
            for overtime_attendance_record in overtime_attendance:
                print(f"overtime_attendance_record: {overtime_attendance_record}")
                if overtime_attendance_record.get('activity_type') == overtime_15:
                    salary_slip.append('regular_overtime', {
                        'timesheet': overtime_attendance_record.get('name'),
                        'hours': overtime_attendance_record.get('total_hours')
                    })
                    salary_slip.overtime_hours += overtime_attendance_record.get('total_hours')

                if overtime_attendance_record.get('activity_type') == overtime_20:
                    salary_slip.append('holiday_overtime', {
                        'timesheet': overtime_attendance_record.get('name'),
                        'hours': overtime_attendance_record.get('total_hours')
                    })
                    salary_slip.holiday_hours += overtime_attendance_record.get('total_hours')
        
        if salary_slip.regular_working_hours > maximum_monthly_hours:
            # salary_slip.overtime_hours += salary_slip.regular_working_hours - maximum_monthly_hours
            salary_slip.regular_working_hours = maximum_monthly_hours
        elif salary_slip.regular_working_hours < maximum_monthly_hours:
            balance_to_maximum_monthly_hours = maximum_monthly_hours - salary_slip.regular_working_hours
            if salary_slip.overtime_hours <= balance_to_maximum_monthly_hours:
                salary_slip.regular_working_hours += salary_slip.overtime_hours
                salary_slip.overtime_hours = 0
            else:
                salary_slip.overtime_hours -= balance_to_maximum_monthly_hours
                salary_slip.regular_working_hours += balance_to_maximum_monthly_hours



        if salary_slip.attendance or salary_slip.regular_overtime or salary_slip.holiday_overtime:
            salary_slip.save(ignore_permissions=True)
            frappe.db.commit()

def check_add_hour():
    shift_type_doc = frappe.get_doc("Shift Type", "Ca 9-18h")
    attendance_doc = frappe.get_doc("Attendance", "HR-ATT-2025-00805")
    in_time_str = str(attendance_doc.in_time).split(".")[0]
    in_time = datetime.strptime(in_time_str, '%Y-%m-%d %H:%M:%S')
    # shift_end_time = datetime.strptime(str(entry.shift_end_time), '%H:%M:%S').time()
    # shift_end_time = shift_start_time.hour + entry.total_shift_hours
    shift_end_time_date_time = in_time + timedelta(hours=shift_type_doc.total_shift_hours)
    shift_end_time = shift_end_time_date_time.time()

    print(f"in_time: {in_time} shift_end_time_date_time: {shift_end_time_date_time} shift_end_time:{shift_end_time}")
