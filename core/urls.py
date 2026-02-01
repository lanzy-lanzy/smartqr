from django.urls import path
from . import views
from . import api

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Supplies
    path('supplies/', views.supplies_list, name='supplies'),
    path('supplies/<int:pk>/', views.supply_detail, name='supply_detail'),
    path('equipment/', views.equipment_list, name='equipment'),
    path('equipment/<int:pk>/', views.equipment_detail, name='equipment_detail'),
    path('equipment/<int:pk>/qr/', views.equipment_qr, name='equipment_qr'),
    path('categories/', views.categories_list, name='categories'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Supplies CRUD
    path('supplies/new/', views.supply_create, name='supply_create'),
    path('supplies/<int:pk>/edit/', views.supply_edit, name='supply_edit'),
    path('supplies/<int:pk>/delete/', views.supply_delete, name='supply_delete'),
    
    # Equipment Instances CRUD
    path('equipment/new/', views.instance_create, name='instance_create'),
    path('equipment/<int:pk>/edit/', views.instance_edit, name='instance_edit'),
    path('equipment/<int:pk>/delete/', views.instance_delete, name='instance_delete'),
    
    # Requests - User
    path('requests/new/', views.request_create, name='request_create'),
    path('requests/my/', views.my_requests, name='my_requests'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/qr/', views.request_qr, name='request_qr'),
    
    # Requests - GSO Staff
    path('requests/pending/', views.pending_requests, name='pending_requests'),
    path('requests/pending/export/', views.export_pending_requests, name='export_pending_requests'),
    path('requests/<int:pk>/approve/', views.approve_request, name='approve_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('requests/<int:pk>/cancel/', views.cancel_request, name='cancel_request'),
    path('requests/batch-approve/', views.batch_approve_requests_view, name='batch_approve_requests'),
    path('requests/batch-reject/', views.batch_reject_requests_view, name='batch_reject_requests'),
    
    # Extensions
    path('extensions/request/<int:borrowed_item_id>/', views.request_extension, name='request_extension'),
    path('extensions/', views.extensions_list, name='extensions'),
    path('extensions/<int:pk>/approve/', views.approve_extension, name='approve_extension'),
    path('extensions/<int:pk>/reject/', views.reject_extension, name='reject_extension'),
    
    # QR Scanner & Borrowing
    path('scanner/', views.qr_scanner, name='qr_scanner'),
    path('scanner/process/', views.process_qr_scan, name='process_qr_scan'),
    path('scanner/issue/', views.issue_item, name='issue_item'),
    
    # Returns
    path('returns/', views.returns_list, name='returns'),
    path('returns/process/', views.process_return, name='process_return'),
    path('returns/scanner/', views.return_scanner, name='return_scanner'),
    path('returns/scan/', views.process_return_scan, name='process_return_scan'),
    path('returns/confirm/', views.confirm_return, name='confirm_return'),
    
    # Batch Requests
    path('requests/batch/new/', views.batch_request_create, name='batch_request_create'),
    path('requests/batch/<uuid:batch_id>/', views.batch_request_detail, name='batch_request_detail'),
    path('requests/batch/<uuid:batch_id>/approve/', views.batch_approve, name='batch_approve'),
    path('requests/batch/<uuid:batch_id>/reject/', views.batch_reject, name='batch_reject'),
    path('requests/batch/<uuid:batch_id>/issue/', views.batch_issue, name='batch_issue'),
    path('requests/batch/<uuid:batch_id>/return/', views.batch_return, name='batch_return'),
    path('requests/batch/<uuid:batch_id>/status/', views.batch_return_status, name='batch_return_status'),
    
    # Admin
    path('users/', views.users_list, name='users'),
    path('users/<int:pk>/approve/', views.approve_user, name='approve_user'),
    path('departments/', views.departments_list, name='departments'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    
    # Reports & Export
    path('reports/', views.reports_list, name='reports'),
    path('reports/inventory/', views.report_inventory, name='report_inventory'),
    path('reports/borrowing/', views.report_borrowing, name='report_borrowing'),
    path('reports/analytics/', views.report_analytics, name='report_analytics'),
    path('reports/qr-sheet/', views.report_qr_sheet, name='report_qr_sheet'),
    
    # Export CSV
    path('export/supplies/', views.export_supplies, name='export_supplies'),
    path('export/equipment/', views.export_equipment, name='export_equipment'),
    path('export/requests/', views.export_requests, name='export_requests'),
    path('export/borrowed/', views.export_borrowed, name='export_borrowed'),
    
    # Import CSV
    path('import/', views.import_view, name='import'),
    path('import/template/<str:template_type>/', views.import_template, name='import_template'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    path('notifications/delete-read/', views.notification_delete_all_read, name='notification_delete_all_read'),
    path('notifications/dropdown/', views.notifications_dropdown, name='notifications_dropdown'),
    
    # Internal API (for AJAX/HTMX)
    path('api/supplies/search/', views.api_supplies_search, name='api_supplies_search'),
    path('api/supplies/<int:supply_id>/instances/', views.api_instances_for_supply, name='api_instances_for_supply'),
    path('api/chart-data/', views.api_chart_data, name='api_chart_data'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    
    # REST API v1
    path('api/v1/supplies/', api.api_supplies_list, name='api_v1_supplies'),
    path('api/v1/supplies/<int:pk>/', api.api_supply_detail, name='api_v1_supply_detail'),
    path('api/v1/ai/suggest-supply/', api.api_ai_suggest_supply, name='api_ai_suggest_supply'),
    path('api/v1/ai/suggest-prefix/', api.api_ai_suggest_prefix, name='api_ai_suggest_prefix'),
    path('api/v1/ai/suggest-serials/', api.api_ai_suggest_serials, name='api_ai_suggest_serials'),
    path('api/v1/ai/suggest-category/', api.api_ai_suggest_category, name='api_ai_suggest_category'),
    path('api/v1/instances/', api.api_instances_list, name='api_v1_instances'),
    path('api/v1/requests/', api.api_requests_list, name='api_v1_requests'),
    path('api/v1/requests/<int:pk>/', api.api_request_detail, name='api_v1_request_detail'),
    path('api/v1/requests/<int:pk>/approve/', api.api_request_approve, name='api_v1_request_approve'),
    path('api/v1/requests/<int:pk>/reject/', api.api_request_reject, name='api_v1_request_reject'),
    path('api/v1/borrowed/', api.api_borrowed_list, name='api_v1_borrowed'),
    path('api/v1/stats/', api.api_stats, name='api_v1_stats'),
]
