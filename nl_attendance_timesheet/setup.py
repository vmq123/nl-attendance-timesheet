import os
import click

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.install_fixtures import (
	_,  # NOTE: this is not the real translation function
)
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.installer import update_site_config


def after_install():
	try:
		print("Setting up NL_Attendance_TS...")
		execute_after_install()

		click.secho("Thank you for installing NL_Attendance_TS!", fg="green")

	except Exception as e:
		BUG_REPORT_URL = "https://github.com/vmq123/maika/issues/new"
		click.secho(
			"Installation for NL_Attendance_TS app failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e

def execute_after_install():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	# create_salary_slip_loan_fields()
	# make_fixtures()
	# setup_notifications()
	update_nl_attendance_ts_defaults()
	# add_non_standard_user_types()
	# set_single_defaults()
	# create_default_role_profiles()
	# create_default_module_profiles()
	# run_post_install_patches()


def before_uninstall():
	delete_custom_fields(get_custom_fields())
	delete_custom_fields(get_salary_slip_loan_fields())
	# delete_company_fixtures()


def after_app_install(app_name):
	"""Set up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	create_custom_fields(get_salary_slip_loan_fields(), ignore_validate=True)
	add_lending_docperms_to_ess()


def before_app_uninstall(app_name):
	"""Clean up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	delete_custom_fields(get_salary_slip_loan_fields())
	remove_lending_docperms_from_ess()


def get_custom_fields():
	"""Maika specific custom fields that need to be added to the masters in ERPNext"""
	return {
        "Attendance": [
            {
                "fieldname": "payment_hours",
                "fieldtype": "Float",
                "label": "Payment Hours",
                "translatable": 1,
                "read_only": 1,
                "insert_after": "working_hours"
            },
            {
                "fieldname": "overtime",
                "fieldtype": "Float",
                "translatable": 1,
                "read_only": 1,
                "insert_after": "payment_hours",
            }
        ],
        "Salary Slip": [
            {
                "fieldname": "wage_based_salary_hours",
                "fieldtype": "Check",
                "label": "Wage based salary (hours)",
                "translatable": 1,
                "read_only": 1,
                "fetch_from": "salary_structure.wage_based_salary_hours",
                "insert_after": "salary_slip_based_on_timesheet"
            },
            {
                "fieldname": "attendance_details_tab_break",
                "fieldtype": "Tab Break",
                "label": "Attendance Details",
                "translatable": 1,
                "depends_on": "eval:doc.wage_based_salary_hours",
                "insert_after": "deduct_tax_for_unsubmitted_tax_exemption_proof"
            },
            {
                "fieldname": "attendance_section",
                "fieldtype": "Section Break",
                "insert_after": "attendance_details_tab_break",
                "label": "Attendance",
                "collapsible": 1
            },
            {
                "fieldname": "attendance",
                "fieldtype": "Table",
                "options": "Navari Attendance",
                "label": "Attendance",
                "translatable": 1,
                "insert_after": "attendance_section"
            },
            {
                "fieldname": "overtime_section",
                "fieldtype": "Section Break",
                "insert_after": "attendance",
                "label": "Overtime Details",
                "collapsible": 1
            },
            {
                "fieldname": "regular_overtime",
                "fieldtype": "Table",
                "options": "Regular Overtime",
                "label": "Overtime 1.5",
                "translatable": 1,
                "insert_after": "overtime_section"
            },
            {
                "fieldname": "navari_vf_cb_ss_02",
                "fieldtype": "Column Break",
                "insert_after": "regular_overtime"
            },
            {
                "fieldname": "holiday_overtime",
                "fieldtype": "Table",
                "options": "Holiday Overtime",
                "label": "Overtime 2.0",
                "translatable": 1,
                "insert_after": "navari_vf_cb_ss_02"
            },
            {
                "fieldname": "worked_hours_summary_section",
                "fieldtype": "Section Break",
                "insert_after": "holiday_overtime",
                "label": "Worked Hours Summary",
                "collapsible": 1
            },
            {
                "fieldname": "regular_working_hours",
                "fieldtype": "Float",
                "label": "Regular Working Hours",
                "translatable": 1,
                "read_only": 1,
                "insert_after": "worked_hours_summary_section"
            },
            {
                "fieldname": "overtime_hours",
                "fieldtype": "Float",
                "label": "Overtime Hours",
                "translatable": 1,
                "read_only": 1,
                "insert_after": "regular_working_hours"
            },
            {
                "fieldname": "holiday_hours",
                "fieldtype": "Float",
                "label": "Holiday Hours",
                "translatable": 1,
                "read_only": 1, 
                "insert_after": "overtime_hours"
            },
            {
                "fieldname": "navari_vf_cb_ss_01",
                "fieldtype": "Column Break",
                "insert_after": "holiday_hours"
            },
            {
                "fieldname": "hourly_rate",
                "fieldtype": "Currency",
                "label": "Hourly Rate",
                "translatable": 1,
                "fetch_from": "salary_structure.hourly_rate",
                "insert_after": "navari_vf_cb_ss_01"
            },
            {
                "fieldname": "incentive_based_salary",
                "fieldtype": "Check",
                "label": "Incentive based salary",
                "translatable": 1,
                "read_only": 1,
                "fetch_from": "salary_structure.incentive_based_salary",
                "insert_after": "wage_based_salary_hours"
            },
            {
                "fieldname": "incentives_details_tab_break",
                "fieldtype": "Tab Break",
                "label": "Incentives Details",
                "translatable": 1,
                "insert_after": "hourly_rate"
            },
            {
                "fieldname": "incentives_section",
                "fieldtype": "Section Break",
                "insert_after": "incentives_details_tab_break",
                "label": "Incentive",
                "collapsible": 1
            },
            {
                "fieldname": "incentive",
                "fieldtype": "Table",
                "options": "MK Sales Incentive",
                "label": "Incentive",
                "translatable": 1,
                "insert_after": "incentives_section"
            },
            {
                "fieldname": "incentives_summary_section",
                "fieldtype": "Section Break",
                "insert_after": "incentive",
                "label": "Incentives Summary",
                "collapsible": 1
            },
            {
                "fieldname": "incentives_total",
                "fieldtype": "Currency",
                "label": "Total Incentives",
                "translatable": 1,
                "read_only": 1,
                "insert_after": "incentives_summary_section"
            },
        ],
        "Salary Structure": [
            {
                "fieldname": "wage_based_salary_hours",
                "fieldtype": "Check",
                "label": "Wage based salary (hours)",
                "translatable": 1,
                "insert_after": "salary_slip_based_on_timesheet",
            },
            {
                "fieldname": "hourly_rate",
                "fieldtype": "Currency",
                "label": "Hourly Rate",
                "translatable": 1,
                "insert_after": "wage_based_salary_hours",
            },
            {
                "fieldname": "incentive_based_salary",
                "fieldtype": "Check",
                "label": "Incentive based salary",
                "translatable": 1,
                "insert_after": "hourly_rate",
            }
        ],
        "Shift Type": [
            {
                "fieldname": "total_shift_hours",
                "fieldtype": "Float",
                "label": "Total shift hours",
                "translatable": 1,
                "insert_after": "end_time"
            },
            {
                "fieldname": "include_unpaid_breaks",
                "fieldtype": "Check",
                "label": "Include Unpaid Breaks",
                "translatable": 1,
                "insert_after": "total_shift_hours"
            },
            {
                "fieldname": "unpaid_breaks_minutes",
                "fieldtype": "Float",
                "label": "Unpaid breaks (minutes)",
                "translatable": 1,
                "depends_on": "eval: doc.include_unpaid_breaks",
                "insert_after": "include_unpaid_breaks"
            },
            {
                "fieldname": "min_hours_to_include_a_break",
                "fieldtype": "Float",
                "label": "Min. hours to include a break",
                "translatable": 1,
                "depends_on": "eval: doc.include_unpaid_breaks",
                "insert_after": "unpaid_breaks_minutes"
            }
        ],
        "Timesheet": [
            {
                "fieldname": "attendance",
                "fieldtype": "Link",
                "options": "Attendance",
                "label": "Attendance",
                "translatable": 1,
                "hidden": 1,
                "read_only": 1,
                "unique": 1,
                "insert_after": "note"
            }
        ],
        "Navari Custom Payroll Settings": [
         {
                "fieldname": "overtime_threshold",
                "fieldtype": "Float",
                "label": "Overtime Threshold",
                "insert_after": "include_early_entry",
                "default": "30.0"
            }
        ],
	}


def make_fixtures():
	records = [
		# expense claim type
		{"doctype": "Expense Claim Type", "name": _("Calls"), "expense_type": _("Calls")},
		{"doctype": "Expense Claim Type", "name": _("Food"), "expense_type": _("Food")},
		{"doctype": "Expense Claim Type", "name": _("Medical"), "expense_type": _("Medical")},
		{"doctype": "Expense Claim Type", "name": _("Others"), "expense_type": _("Others")},
		{"doctype": "Expense Claim Type", "name": _("Travel"), "expense_type": _("Travel")},
		# vehicle service item
		{"doctype": "Vehicle Service Item", "service_item": "Brake Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Brake Pad"},
		{"doctype": "Vehicle Service Item", "service_item": "Clutch Plate"},
		{"doctype": "Vehicle Service Item", "service_item": "Engine Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Oil Change"},
		{"doctype": "Vehicle Service Item", "service_item": "Wheels"},
		# leave type
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Casual Leave"),
			"name": _("Casual Leave"),
			"allow_encashment": 1,
			"is_carry_forward": 1,
			"max_continuous_days_allowed": "3",
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Compensatory Off"),
			"name": _("Compensatory Off"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
			"is_compensatory": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Sick Leave"),
			"name": _("Sick Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Privilege Leave"),
			"name": _("Privilege Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Leave Without Pay"),
			"name": _("Leave Without Pay"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"is_lwp": 1,
			"include_holiday": 1,
		},
		# Employment Type
		{"doctype": "Employment Type", "employee_type_name": _("Full-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Part-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Probation")},
		{"doctype": "Employment Type", "employee_type_name": _("Contract")},
		{"doctype": "Employment Type", "employee_type_name": _("Commission")},
		{"doctype": "Employment Type", "employee_type_name": _("Piecework")},
		{"doctype": "Employment Type", "employee_type_name": _("Intern")},
		{"doctype": "Employment Type", "employee_type_name": _("Apprentice")},
		# Job Applicant Source
		{"doctype": "Job Applicant Source", "source_name": _("Website Listing")},
		{"doctype": "Job Applicant Source", "source_name": _("Walk In")},
		{"doctype": "Job Applicant Source", "source_name": _("Employee Referral")},
		{"doctype": "Job Applicant Source", "source_name": _("Campaign")},
		# Offer Term
		{"doctype": "Offer Term", "offer_term": _("Date of Joining")},
		{"doctype": "Offer Term", "offer_term": _("Annual Salary")},
		{"doctype": "Offer Term", "offer_term": _("Probationary Period")},
		{"doctype": "Offer Term", "offer_term": _("Employee Benefits")},
		{"doctype": "Offer Term", "offer_term": _("Working Hours")},
		{"doctype": "Offer Term", "offer_term": _("Stock Options")},
		{"doctype": "Offer Term", "offer_term": _("Department")},
		{"doctype": "Offer Term", "offer_term": _("Job Description")},
		{"doctype": "Offer Term", "offer_term": _("Responsibilities")},
		{"doctype": "Offer Term", "offer_term": _("Leaves per Year")},
		{"doctype": "Offer Term", "offer_term": _("Notice Period")},
		{"doctype": "Offer Term", "offer_term": _("Incentives")},
		# Email Account
		{"doctype": "Email Account", "email_id": "jobs@example.com", "append_to": "Job Applicant"},
	]

	make_records(records)


def setup_notifications():
	base_path = frappe.get_app_path("hrms", "hr", "doctype")

	# Leave Application
	response = frappe.read_file(
		os.path.join(base_path, "leave_application/leave_application_email_template.html")
	)
	records = [
		{
			"doctype": "Email Template",
			"name": _("Leave Approval Notification"),
			"response": response,
			"subject": _("Leave Approval Notification"),
			"owner": frappe.session.user,
		}
	]
	records += [
		{
			"doctype": "Email Template",
			"name": _("Leave Status Notification"),
			"response": response,
			"subject": _("Leave Status Notification"),
			"owner": frappe.session.user,
		}
	]

	# Interview
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_reminder_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Reminder"),
			"response": response,
			"subject": _("Interview Reminder"),
			"owner": frappe.session.user,
		}
	]
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_feedback_reminder_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Feedback Reminder"),
			"response": response,
			"subject": _("Interview Feedback Reminder"),
			"owner": frappe.session.user,
		}
	]

	# Exit Interview
	response = frappe.read_file(
		os.path.join(base_path, "exit_interview/exit_questionnaire_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Exit Questionnaire Notification"),
			"response": response,
			"subject": _("Exit Questionnaire Notification"),
			"owner": frappe.session.user,
		}
	]

	make_records(records)


def update_nl_attendance_ts_defaults():
	singles_entry = frappe.get_doc({
        "doctype": "Navari Custom Payroll Settings",
        "doctype_or_field": "Singles",
        "fieldname": "overtime_threshold",
        "value": "30.0"
    })
	singles_entry.insert()


def set_single_defaults():
	for dt in ("HR Settings", "Payroll Settings"):
		default_values = frappe.get_all(
			"DocField",
			filters={"parent": dt},
			fields=["fieldname", "default"],
			as_list=True,
		)
		if default_values:
			try:
				doc = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					doc.set(fieldname, value)
				doc.flags.ignore_mandatory = True
				doc.save()
			except frappe.ValidationError:
				pass


def create_default_role_profiles():
	for role_profile_name, roles in DEFAULT_ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", role_profile_name):
			continue

		role_profile = frappe.new_doc("Role Profile")
		role_profile.role_profile = role_profile_name
		for role in roles:
			role_profile.append("roles", {"role": role})

		role_profile.insert(ignore_permissions=True)

def create_default_module_profiles():
	for module_profile_name, modules in DEFAULT_MODULE_PROFILES.items():
		if frappe.db.exists("Module Profile", module_profile_name):
			continue

		module_profile = frappe.new_doc("Module Profile")
		module_profile.module_profile = module_profile_name
		for module in modules:
			module_profile.append("modules", {"module": module})

		module_profile.insert(ignore_permissions=True)

def get_post_install_patches():
	return (
		"erpnext.patches.v13_0.move_tax_slabs_from_payroll_period_to_income_tax_slab",
		"erpnext.patches.v13_0.move_doctype_reports_and_notification_from_hr_to_payroll",
		"erpnext.patches.v13_0.move_payroll_setting_separately_from_hr_settings",
		"erpnext.patches.v13_0.update_start_end_date_for_old_shift_assignment",
		"erpnext.patches.v13_0.updates_for_multi_currency_payroll",
		"erpnext.patches.v13_0.update_reason_for_resignation_in_employee",
		"erpnext.patches.v13_0.set_company_in_leave_ledger_entry",
		"erpnext.patches.v13_0.rename_stop_to_send_birthday_reminders",
		"erpnext.patches.v13_0.set_training_event_attendance",
		"erpnext.patches.v14_0.set_payroll_cost_centers",
		"erpnext.patches.v13_0.update_employee_advance_status",
		"erpnext.patches.v13_0.update_expense_claim_status_for_paid_advances",
		"erpnext.patches.v14_0.delete_employee_transfer_property_doctype",
		"erpnext.patches.v13_0.set_payroll_entry_status",
		# HRMS
		"create_country_fixtures",
		"update_allocate_on_in_leave_type",
		"update_performance_module_changes",
	)


def run_post_install_patches():
	print("\nPatching Existing Data...")

	POST_INSTALL_PATCHES = get_post_install_patches()
	frappe.flags.in_patch = True

	try:
		for patch in POST_INSTALL_PATCHES:
			patch_name = patch.split(".")[-1]
			if not patch_name:
				continue

			frappe.get_attr(f"hrms.patches.post_install.{patch_name}.execute")()
	finally:
		frappe.flags.in_patch = False


# LENDING APP SETUP & CLEANUP
def create_salary_slip_loan_fields():
	if "lending" in frappe.get_installed_apps():
		create_custom_fields(get_salary_slip_loan_fields(), ignore_validate=True)


def add_lending_docperms_to_ess():
	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()
	append_docperms_to_user_type(loan_docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def remove_lending_docperms_from_ess():
	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()

	for row in list(doc.user_doctypes):
		if row.document_type in loan_docperms:
			doc.user_doctypes.remove(row)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


# ESS USER TYPE SETUP & CLEANUP
def add_non_standard_user_types():
	user_types = get_user_types_data()
	update_user_type_doctype_limit(user_types)

	for user_type, data in user_types.items():
		create_custom_role(data)
		create_user_type(user_type, data)


def update_user_type_doctype_limit(user_types=None):
	if not user_types:
		user_types = get_user_types_data()

	user_type_limit = {}
	for user_type, __ in user_types.items():
		user_type_limit.setdefault(frappe.scrub(user_type), 40)

	update_site_config("user_type_doctype_limit", user_type_limit)


def get_user_types_data():
	return {
		"Employee Self Service": {
			"role": "Employee Self Service",
			"apply_user_permission_on": "Employee",
			"user_id_field": "user_id",
			"doctypes": {
				# masters
				"Holiday List": ["read"],
				"Employee": ["read", "write"],
				"Company": ["read"],
				# payroll
				"Salary Slip": ["read"],
				"Employee Benefit Application": ["read", "write", "create", "delete"],
				# expenses
				"Expense Claim": ["read", "write", "create", "delete"],
				"Expense Claim Type": ["read"],
				"Employee Advance": ["read", "write", "create", "delete"],
				# leave and attendance
				"Leave Application": ["read", "write", "create", "delete"],
				"Attendance Request": ["read", "write", "create", "delete"],
				"Compensatory Leave Request": ["read", "write", "create", "delete"],
				# tax
				"Employee Tax Exemption Declaration": ["read", "write", "create", "delete"],
				"Employee Tax Exemption Proof Submission": ["read", "write", "create", "delete"],
				# projects
				"Timesheet": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# trainings
				"Training Program": ["read"],
				"Training Feedback": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# shifts
				"Employee Checkin": ["read"],
				"Shift Request": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# misc
				"Employee Grievance": ["read", "write", "create", "delete"],
				"Employee Referral": ["read", "write", "create", "delete"],
				"Travel Request": ["read", "write", "create", "delete"],
			},
		}
	}


def get_lending_docperms_for_ess():
	return {
		"Loan": ["read"],
		"Loan Application": ["read", "write", "create", "delete", "submit"],
		"Loan Product": ["read"],
	}


def create_custom_role(data):
	if data.get("role") and not frappe.db.exists("Role", data.get("role")):
		frappe.get_doc(
			{"doctype": "Role", "role_name": data.get("role"), "desk_access": 1, "is_custom": 1}
		).insert(ignore_permissions=True)


def create_user_type(user_type, data):
	if frappe.db.exists("User Type", user_type):
		doc = frappe.get_cached_doc("User Type", user_type)
		doc.user_doctypes = []
	else:
		doc = frappe.new_doc("User Type")
		doc.update(
			{
				"name": user_type,
				"role": data.get("role"),
				"user_id_field": data.get("user_id_field"),
				"apply_user_permission_on": data.get("apply_user_permission_on"),
			}
		)

	docperms = data.get("doctypes")
	if doc.role == "Employee Self Service" and "lending" in frappe.get_installed_apps():
		docperms.update(get_lending_docperms_for_ess())

	append_docperms_to_user_type(docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def append_docperms_to_user_type(docperms, doc):
	existing_doctypes = [d.document_type for d in doc.user_doctypes]

	for doctype, perms in docperms.items():
		if doctype in existing_doctypes:
			continue

		args = {"document_type": doctype}
		for perm in perms:
			args[perm] = 1

		doc.append("user_doctypes", args)


def update_select_perm_after_install():
	if not frappe.flags.update_select_perm_after_migrate:
		return

	frappe.flags.ignore_select_perm = False
	for row in frappe.get_all("User Type", filters={"is_standard": 0}):
		print("Updating user type :- ", row.name)
		doc = frappe.get_doc("User Type", row.name)
		doc.flags.ignore_links = True
		doc.save()

	frappe.flags.update_select_perm_after_migrate = False


def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)


DEFAULT_ROLE_PROFILES = {
	"MK HR": [
		"MK HR User",
		"MK Employee",
		# "Leave Approver",
		# "Expense Approver",
	],
	"MK Employee": [
		"MK Employee",
		# "Leave Approver",
		# "Expense Approver",
	],
	"MK Manager": [
		"MK Employee",
		"MK Accounts User",
		"MK HR Manager",
		"MK HR User",
		"MK Manager",
	],
}

DEFAULT_MODULE_PROFILES = {
	"MK": [
		"Maika",
	],
}

def get_salary_slip_loan_fields():
	return {
		"Salary Slip": [
			{
				"fieldname": "loan_repayment_sb_1",
				"fieldtype": "Section Break",
				"label": _("Loan Repayment"),
				"depends_on": "total_loan_repayment",
				"insert_after": "base_total_deduction",
			},
			{
				"fieldname": "loans",
				"fieldtype": "Table",
				"label": _("Employee Loan"),
				"options": "Salary Slip Loan",
				"print_hide": 1,
				"insert_after": "loan_repayment_sb_1",
			},
			{
				"fieldname": "loan_details_sb_1",
				"fieldtype": "Section Break",
				"depends_on": "eval:doc.docstatus != 0",
				"insert_after": "loans",
			},
			{
				"fieldname": "total_principal_amount",
				"fieldtype": "Currency",
				"label": _("Total Principal Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_details_sb_1",
			},
			{
				"fieldname": "total_interest_amount",
				"fieldtype": "Currency",
				"label": _("Total Interest Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "total_principal_amount",
			},
			{
				"fieldname": "loan_cb_1",
				"fieldtype": "Column Break",
				"insert_after": "total_interest_amount",
			},
			{
				"fieldname": "total_loan_repayment",
				"fieldtype": "Currency",
				"label": _("Total Loan Repayment"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_cb_1",
			},
		],
		"Loan": [
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "status",
			},
		],
		"Loan Repayment": [
			{
				"default": "0",
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "is_term_loan",
			},
			{
				"depends_on": "eval:doc.repay_from_salary",
				"fieldname": "payroll_payable_account",
				"fieldtype": "Link",
				"label": _("Payroll Payable Account"),
				"mandatory_depends_on": "eval:doc.repay_from_salary",
				"options": "Account",
				"insert_after": "payment_account",
			},
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "process_payroll_accounting_entry_based_on_employee",
				"hidden": 1,
				"fieldtype": "Check",
				"label": _("Process Payroll Accounting Entry based on Employee"),
				"insert_after": "repay_from_salary",
			},
		],
	}
