app_name = "delivery_app"
app_title = "Delivery App"
app_publisher = "Muhammad Ardhan"
app_description = "Aplikasi Delivery"
app_email = "ardhanaulia@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {
	"Delivery Note": "public/js/delivery_note.js"
}

# Installation & Migrations
# -------------------------
after_install = "delivery_app.setup.ensure_custom_fields"
after_migrate = "delivery_app.setup.ensure_custom_fields"

# Document Events
# ---------------
doc_events = {
	"Delivery Trip": {
		"validate": "delivery_app.overrides.delivery_trip.validate_delivery_trip"
	}
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"hourly": [
		"delivery_app.services.biteship.sync_active_shipments"
	]
}

# website_generators = ["Web Page"]

# SPA Routing for Fleet-Ops Delivery Console
website_route_rules = [
	{"from_route": "/delivery/<path:app_path>", "to_route": "delivery"},
]

website_redirects = [
	{"source": r"/app/delivery_app", "target": r"/delivery"},
]

add_to_apps_screen = [
	{
		"name": "delivery_app",
		"title": "Delivery Console",
		"route": "/delivery",
	}
]


# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "delivery_app.utils.jinja_methods",
# 	"filters": "delivery_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "delivery_app.install.before_install"
# after_install = "delivery_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "delivery_app.uninstall.before_uninstall"
# after_uninstall = "delivery_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "delivery_app.utils.before_app_install"
# after_app_install = "delivery_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "delivery_app.utils.before_app_uninstall"
# after_app_uninstall = "delivery_app.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "delivery_app.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "delivery_app.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["delivery_app.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"delivery_app.tasks.all"
# 	],
# 	"daily": [
# 		"delivery_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"delivery_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"delivery_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"delivery_app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "delivery_app.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "delivery_app.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "delivery_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "delivery_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["delivery_app.utils.before_request"]
# after_request = ["delivery_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["delivery_app.utils.before_job"]
# after_job = ["delivery_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"delivery_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

