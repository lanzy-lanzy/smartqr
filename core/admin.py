from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import (
    Department,
    User,
    SupplyCategory,
    Supply,
    EquipmentInstance,
    SupplyRequest,
    BorrowedItem,
    QRScanLog,
    InventoryTransaction,
    RequestorBorrowerAnalytics,
    StockAdjustment,
    ExtensionRequest,
    AuditLog,
    Notification,
)


# =============================================================================
# Inline Admins
# =============================================================================

class EquipmentInstanceInline(admin.TabularInline):
    """Inline admin for managing equipment instances within Supply."""
    model = EquipmentInstance
    extra = 0
    fields = ['instance_code', 'serial_number', 'status', 'condition_notes', 'is_active']
    readonly_fields = ['last_borrowed_at', 'last_returned_at']
    show_change_link = True


class BorrowedItemInline(admin.TabularInline):
    """Inline admin for viewing borrowed items within SupplyRequest."""
    model = BorrowedItem
    extra = 0
    fields = ['equipment_instance', 'borrowed_at', 'return_deadline', 'returned_at', 'return_status']
    readonly_fields = ['borrowed_at']
    show_change_link = True


class InventoryTransactionInline(admin.TabularInline):
    """Inline admin for viewing transactions within Supply."""
    model = InventoryTransaction
    extra = 0
    fields = ['transaction_type', 'quantity', 'previous_quantity', 'new_quantity', 'performed_by', 'performed_at']
    readonly_fields = ['performed_at']
    show_change_link = True
    max_num = 10


# =============================================================================
# Department Admin
# =============================================================================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'user_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'


# =============================================================================
# User Admin
# =============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'get_full_name', 'role', 'department', 
        'approval_status_badge', 'is_active', 'has_overdue_badge'
    ]
    list_filter = ['role', 'approval_status', 'is_active', 'is_staff', 'department']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone', 'profile_picture')
        }),
        ('Role & Department', {
            'fields': ('role', 'department', 'approval_status')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 
                'first_name', 'last_name', 
                'role', 'department', 'approval_status'
            ),
        }),
    )

    def approval_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.approval_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_approval_status_display()
        )
    approval_status_badge.short_description = 'Status'

    def has_overdue_badge(self, obj):
        if obj.has_overdue_items:
            count = obj.overdue_items.count()
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">{} Overdue</span>',
                count
            )
        return format_html(
            '<span style="color: green;">OK</span>'
        )
    has_overdue_badge.short_description = 'Overdue'


# =============================================================================
# Supply Category Admin
# =============================================================================

@admin.register(SupplyCategory)
class SupplyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type_badge', 'supply_count', 'is_active']
    list_filter = ['is_material', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'icon')
        }),
        ('Type', {
            'fields': ('is_material',),
            'description': 'If checked, items in this category are borrowable equipment that must be returned.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def category_type_badge(self, obj):
        if obj.is_material:
            return format_html(
                '<span style="background-color: #4f46e5; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">Equipment</span>'
            )
        return format_html(
            '<span style="background-color: #059669; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">Consumable</span>'
        )
    category_type_badge.short_description = 'Type'

    def supply_count(self, obj):
        return obj.supplies.count()
    supply_count.short_description = 'Items'


# =============================================================================
# Supply Admin
# =============================================================================

@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'stock_status_badge', 
        'quantity', 'available_quantity', 'min_stock_level',
        'is_consumable', 'is_active'
    ]
    list_filter = ['category', 'is_consumable', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    readonly_fields = ['qr_code', 'stock_status', 'available_quantity', 'qr_data']
    inlines = [EquipmentInstanceInline, InventoryTransactionInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category', 'image')
        }),
        ('Stock Management', {
            'fields': ('quantity', 'min_stock_level', 'unit', 'stock_status', 'available_quantity')
        }),
        ('Borrowing Settings', {
            'fields': ('is_consumable', 'default_borrow_days')
        }),
        ('QR Code', {
            'fields': ('qr_data', 'qr_code'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_by')
        }),
    )

    def stock_status_badge(self, obj):
        colors = {
            'in_stock': '#059669',
            'low_stock': '#d97706',
            'out_of_stock': '#dc2626',
        }
        color = colors.get(obj.stock_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_stock_status_display() if hasattr(obj, 'get_stock_status_display') else obj.stock_status.replace('_', ' ').title()
        )
    stock_status_badge.short_description = 'Stock Status'

    actions = ['generate_qr_codes']

    @admin.action(description='Generate QR codes for selected supplies')
    def generate_qr_codes(self, request, queryset):
        count = 0
        for supply in queryset:
            if supply.generate_qr_code():
                supply.save()
                count += 1
        self.message_user(request, f'Generated QR codes for {count} supplies.')


# =============================================================================
# Equipment Instance Admin
# =============================================================================

@admin.register(EquipmentInstance)
class EquipmentInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'instance_code', 'supply', 'serial_number', 
        'status_badge', 'current_borrower_link', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'supply__category', 'supply']
    search_fields = ['instance_code', 'serial_number', 'supply__name']
    ordering = ['supply', 'instance_code']
    readonly_fields = ['qr_code', 'qr_data', 'last_borrowed_at', 'last_returned_at', 'last_borrowed_by']
    
    fieldsets = (
        (None, {
            'fields': ('supply', 'instance_code', 'serial_number')
        }),
        ('Status', {
            'fields': ('status', 'condition_notes', 'is_active')
        }),
        ('QR Code', {
            'fields': ('qr_data', 'qr_code'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('last_borrowed_at', 'last_returned_at', 'last_borrowed_by'),
            'classes': ('collapse',)
        }),
        ('Acquisition', {
            'fields': ('acquired_date', 'warranty_expiry'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'available': '#059669',
            'borrowed': '#3b82f6',
            'maintenance': '#d97706',
            'retired': '#6b7280',
            'lost': '#dc2626',
            'damaged': '#ef4444',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def current_borrower_link(self, obj):
        borrower = obj.current_borrower
        if borrower:
            url = reverse('admin:core_user_change', args=[borrower.pk])
            return format_html('<a href="{}">{}</a>', url, borrower.get_full_name())
        return '-'
    current_borrower_link.short_description = 'Current Borrower'

    actions = ['generate_qr_codes', 'mark_available', 'mark_maintenance']

    @admin.action(description='Generate QR codes for selected instances')
    def generate_qr_codes(self, request, queryset):
        count = 0
        for instance in queryset:
            if instance.generate_qr_code():
                instance.save()
                count += 1
        self.message_user(request, f'Generated QR codes for {count} instances.')

    @admin.action(description='Mark selected as Available')
    def mark_available(self, request, queryset):
        queryset.update(status=EquipmentInstance.Status.AVAILABLE)
        self.message_user(request, f'Marked {queryset.count()} instances as available.')

    @admin.action(description='Mark selected as Under Maintenance')
    def mark_maintenance(self, request, queryset):
        queryset.update(status=EquipmentInstance.Status.MAINTENANCE)
        self.message_user(request, f'Marked {queryset.count()} instances as under maintenance.')


# =============================================================================
# Supply Request Admin
# =============================================================================

@admin.register(SupplyRequest)
class SupplyRequestAdmin(admin.ModelAdmin):
    list_display = [
        'request_code', 'requester', 'supply', 'quantity',
        'status_badge', 'priority_badge', 'requested_at', 'is_batch_request'
    ]
    list_filter = ['status', 'priority', 'requested_at', 'supply__category']
    search_fields = ['request_code', 'requester__email', 'supply__name', 'purpose']
    ordering = ['-requested_at']
    readonly_fields = ['request_code', 'qr_code', 'qr_data', 'requested_at', 'reviewed_at', 'issued_at']
    inlines = [BorrowedItemInline]
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('Request Info', {
            'fields': ('request_code', 'batch_group_id', 'requester')
        }),
        ('Item Details', {
            'fields': ('supply', 'requested_instance', 'quantity', 'purpose', 'priority', 'needed_by')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
        ('Issuance', {
            'fields': ('issued_by', 'issued_at'),
            'classes': ('collapse',)
        }),
        ('QR Code', {
            'fields': ('qr_data', 'qr_code'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': '#d97706',
            'approved': '#059669',
            'rejected': '#dc2626',
            'issued': '#3b82f6',
            'partially_returned': '#8b5cf6',
            'returned': '#10b981',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        colors = {
            'low': '#6b7280',
            'normal': '#3b82f6',
            'high': '#d97706',
            'urgent': '#dc2626',
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    actions = ['approve_requests', 'reject_requests', 'generate_qr_codes']

    @admin.action(description='Approve selected requests')
    def approve_requests(self, request, queryset):
        count = 0
        for req in queryset.filter(status=SupplyRequest.Status.PENDING):
            req.approve(request.user)
            count += 1
        self.message_user(request, f'Approved {count} requests.')

    @admin.action(description='Reject selected requests')
    def reject_requests(self, request, queryset):
        count = queryset.filter(status=SupplyRequest.Status.PENDING).update(
            status=SupplyRequest.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'Rejected {count} requests.')

    @admin.action(description='Generate QR codes for selected requests')
    def generate_qr_codes(self, request, queryset):
        count = 0
        for req in queryset:
            if req.generate_qr_code():
                req.save()
                count += 1
        self.message_user(request, f'Generated QR codes for {count} requests.')


# =============================================================================
# Borrowed Item Admin
# =============================================================================

@admin.register(BorrowedItem)
class BorrowedItemAdmin(admin.ModelAdmin):
    list_display = [
        'equipment_instance', 'borrower', 'borrowed_at', 
        'return_deadline', 'overdue_status', 'return_status_badge', 'returned_at'
    ]
    list_filter = ['return_status', 'borrowed_at', 'returned_at']
    search_fields = [
        'equipment_instance__instance_code', 
        'borrower__email', 
        'request__request_code'
    ]
    ordering = ['-borrowed_at']
    readonly_fields = ['borrowed_at', 'is_overdue', 'days_until_due', 'overdue_days']
    date_hierarchy = 'borrowed_at'
    
    fieldsets = (
        ('Borrow Info', {
            'fields': ('request', 'equipment_instance', 'borrower')
        }),
        ('Dates', {
            'fields': ('borrowed_at', 'return_deadline', 'returned_at')
        }),
        ('Overdue Status', {
            'fields': ('is_overdue', 'days_until_due', 'overdue_days'),
            'classes': ('collapse',)
        }),
        ('Return', {
            'fields': ('return_status', 'return_notes', 'received_by')
        }),
    )

    def overdue_status(self, obj):
        if obj.returned_at:
            return format_html('<span style="color: #6b7280;">Returned</span>')
        if obj.is_overdue:
            return format_html(
                '<span style="background-color: #dc2626; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; animation: pulse 2s infinite;">'
                '{} days overdue</span>',
                obj.overdue_days
            )
        return format_html(
            '<span style="color: #059669;">{} days left</span>',
            obj.days_until_due
        )
    overdue_status.short_description = 'Status'

    def return_status_badge(self, obj):
        colors = {
            'pending': '#d97706',
            'good': '#059669',
            'damaged': '#ef4444',
            'lost': '#dc2626',
        }
        color = colors.get(obj.return_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_return_status_display()
        )
    return_status_badge.short_description = 'Condition'

    actions = ['process_return_good', 'process_return_damaged']

    @admin.action(description='Process return (Good Condition)')
    def process_return_good(self, request, queryset):
        count = 0
        for item in queryset.filter(returned_at__isnull=True):
            item.process_return(request.user, BorrowedItem.ReturnStatus.GOOD)
            count += 1
        self.message_user(request, f'Processed {count} returns as good condition.')

    @admin.action(description='Process return (Damaged)')
    def process_return_damaged(self, request, queryset):
        count = 0
        for item in queryset.filter(returned_at__isnull=True):
            item.process_return(request.user, BorrowedItem.ReturnStatus.DAMAGED, 'Marked as damaged via admin')
            count += 1
        self.message_user(request, f'Processed {count} returns as damaged.')


# =============================================================================
# QR Scan Log Admin
# =============================================================================

@admin.register(QRScanLog)
class QRScanLogAdmin(admin.ModelAdmin):
    list_display = [
        'scanned_at', 'scanned_by', 'scan_type_badge', 
        'qr_data_short', 'was_successful', 'related_item'
    ]
    list_filter = ['scan_type', 'was_successful', 'scanned_at']
    search_fields = ['qr_data', 'scanned_by__email', 'notes']
    ordering = ['-scanned_at']
    readonly_fields = ['scanned_at']
    date_hierarchy = 'scanned_at'
    
    fieldsets = (
        ('Scan Info', {
            'fields': ('scanned_by', 'qr_data', 'scan_type', 'scanned_at')
        }),
        ('Related Objects', {
            'fields': ('supply', 'equipment_instance', 'supply_request'),
            'classes': ('collapse',)
        }),
        ('Result', {
            'fields': ('was_successful', 'error_message', 'notes')
        }),
        ('Technical', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

    def scan_type_badge(self, obj):
        colors = {
            'scan': '#3b82f6',
            'issue': '#059669',
            'return': '#8b5cf6',
            'inventory': '#d97706',
        }
        color = colors.get(obj.scan_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_scan_type_display()
        )
    scan_type_badge.short_description = 'Type'

    def qr_data_short(self, obj):
        if len(obj.qr_data) > 30:
            return f"{obj.qr_data[:30]}..."
        return obj.qr_data
    qr_data_short.short_description = 'QR Data'

    def related_item(self, obj):
        if obj.equipment_instance:
            return obj.equipment_instance.instance_code
        if obj.supply:
            return obj.supply.name
        if obj.supply_request:
            return obj.supply_request.request_code
        return '-'
    related_item.short_description = 'Related'


# =============================================================================
# Inventory Transaction Admin
# =============================================================================

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'performed_at', 'supply', 'transaction_type_badge',
        'quantity_display', 'stock_change', 'performed_by'
    ]
    list_filter = ['transaction_type', 'performed_at', 'supply__category']
    search_fields = ['supply__name', 'reference_code', 'notes']
    ordering = ['-performed_at']
    readonly_fields = ['performed_at']
    date_hierarchy = 'performed_at'
    
    fieldsets = (
        ('Transaction', {
            'fields': ('supply', 'equipment_instance', 'transaction_type', 'quantity')
        }),
        ('Stock Levels', {
            'fields': ('previous_quantity', 'new_quantity')
        }),
        ('Reference', {
            'fields': ('reference_code', 'supply_request', 'borrowed_item', 'notes')
        }),
        ('Tracking', {
            'fields': ('performed_by', 'performed_at')
        }),
    )

    def transaction_type_badge(self, obj):
        colors = {
            'in': '#059669',
            'out': '#dc2626',
            'adjustment': '#d97706',
            'transfer': '#3b82f6',
            'return': '#8b5cf6',
            'damage': '#ef4444',
            'loss': '#7f1d1d',
        }
        color = colors.get(obj.transaction_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = 'Type'

    def quantity_display(self, obj):
        if obj.quantity > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.quantity)
        return format_html('<span style="color: red;">{}</span>', obj.quantity)
    quantity_display.short_description = 'Qty'

    def stock_change(self, obj):
        return f"{obj.previous_quantity} → {obj.new_quantity}"
    stock_change.short_description = 'Stock'


# =============================================================================
# User Analytics Admin
# =============================================================================

@admin.register(RequestorBorrowerAnalytics)
class RequestorBorrowerAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'total_requests', 'total_borrows', 'active_borrows',
        'on_time_rate_display', 'reliability_score_display'
    ]
    list_filter = ['updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-reliability_score']
    readonly_fields = [
        'total_requests', 'approved_requests', 'rejected_requests', 'cancelled_requests',
        'total_borrows', 'active_borrows', 'on_time_returns', 'late_returns',
        'total_overdue_days', 'good_condition_returns', 'damaged_returns', 'lost_items',
        'reliability_score', 'approval_rate', 'on_time_rate', 'damage_rate',
        'last_request_at', 'last_borrow_at', 'last_return_at', 'updated_at'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Request Statistics', {
            'fields': ('total_requests', 'approved_requests', 'rejected_requests', 'cancelled_requests', 'approval_rate')
        }),
        ('Borrowing Statistics', {
            'fields': ('total_borrows', 'active_borrows')
        }),
        ('Return Performance', {
            'fields': ('on_time_returns', 'late_returns', 'total_overdue_days', 'on_time_rate')
        }),
        ('Condition History', {
            'fields': ('good_condition_returns', 'damaged_returns', 'lost_items', 'damage_rate')
        }),
        ('Scores', {
            'fields': ('reliability_score',)
        }),
        ('Timestamps', {
            'fields': ('last_request_at', 'last_borrow_at', 'last_return_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def on_time_rate_display(self, obj):
        rate = obj.on_time_rate
        color = '#059669' if rate >= 90 else '#d97706' if rate >= 70 else '#dc2626'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    on_time_rate_display.short_description = 'On-Time Rate'

    def reliability_score_display(self, obj):
        score = obj.reliability_score
        color = '#059669' if score >= 80 else '#d97706' if score >= 60 else '#dc2626'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{:.1f}</span>',
            color, score
        )
    reliability_score_display.short_description = 'Reliability'

    actions = ['recalculate_scores']

    @admin.action(description='Recalculate reliability scores')
    def recalculate_scores(self, request, queryset):
        for analytics in queryset:
            analytics.recalculate_reliability_score()
        self.message_user(request, f'Recalculated scores for {queryset.count()} users.')


# =============================================================================
# Stock Adjustment Admin
# =============================================================================

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'adjusted_at', 'supply', 'reason_badge', 'quantity',
        'is_penalty', 'responsible_user', 'adjusted_by'
    ]
    list_filter = ['reason', 'is_penalty', 'adjusted_at']
    search_fields = ['supply__name', 'description', 'responsible_user__email']
    ordering = ['-adjusted_at']
    readonly_fields = ['adjusted_at']
    date_hierarchy = 'adjusted_at'
    
    fieldsets = (
        ('Adjustment', {
            'fields': ('supply', 'equipment_instance', 'reason', 'quantity', 'description')
        }),
        ('Penalty', {
            'fields': ('is_penalty', 'penalty_amount', 'responsible_user')
        }),
        ('Reference', {
            'fields': ('borrowed_item',)
        }),
        ('Tracking', {
            'fields': ('adjusted_by', 'adjusted_at')
        }),
    )

    def reason_badge(self, obj):
        colors = {
            'damage': '#ef4444',
            'loss': '#dc2626',
            'theft': '#7f1d1d',
            'expired': '#d97706',
            'correction': '#3b82f6',
            'other': '#6b7280',
        }
        color = colors.get(obj.reason, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_reason_display()
        )
    reason_badge.short_description = 'Reason'


# =============================================================================
# Admin Site Customization
# =============================================================================

admin.site.site_header = 'Smart Supply Management'
admin.site.site_title = 'Smart Supply Admin'
admin.site.index_title = 'Equipment & Inventory Management'


# =============================================================================
# Extension Request Admin
# =============================================================================

@admin.register(ExtensionRequest)
class ExtensionRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'borrowed_item', 'requested_by', 'requested_days',
        'status_badge', 'requested_at', 'reviewed_by'
    ]
    list_filter = ['status', 'requested_at', 'reviewed_at']
    search_fields = [
        'borrowed_item__equipment_instance__instance_code',
        'requested_by__email',
        'reason'
    ]
    ordering = ['-requested_at']
    readonly_fields = ['requested_at', 'reviewed_at', 'original_deadline', 'new_deadline']
    
    fieldsets = (
        ('Request', {
            'fields': ('borrowed_item', 'requested_by', 'requested_days', 'reason')
        }),
        ('Deadlines', {
            'fields': ('original_deadline', 'new_deadline')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': '#d97706',
            'approved': '#059669',
            'rejected': '#dc2626',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# =============================================================================
# Audit Log Admin
# =============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'user_email', 'action_badge', 'entity_type',
        'description_short', 'ip_address'
    ]
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['user_email', 'description', 'entity_repr']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'user', 'user_email', 'action', 'entity_type', 
                       'entity_id', 'entity_repr', 'description', 'changes', 
                       'ip_address', 'user_agent']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Who', {
            'fields': ('user', 'user_email')
        }),
        ('What', {
            'fields': ('action', 'entity_type', 'entity_id', 'entity_repr', 'description')
        }),
        ('Details', {
            'fields': ('changes',),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def action_badge(self, obj):
        colors = {
            'create': '#059669',
            'update': '#3b82f6',
            'delete': '#dc2626',
            'login': '#6366f1',
            'logout': '#6b7280',
            'approve': '#10b981',
            'reject': '#ef4444',
            'issue': '#f59e0b',
            'return': '#8b5cf6',
            'scan': '#06b6d4',
            'export': '#14b8a6',
            'import': '#ec4899',
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def description_short(self, obj):
        if len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    description_short.short_description = 'Description'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# =============================================================================
# Notification Admin
# =============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'notification_type_badge', 'title',
        'is_read', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recipient', {
            'fields': ('user',)
        }),
        ('Content', {
            'fields': ('notification_type', 'title', 'message', 'link')
        }),
        ('Related Objects', {
            'fields': ('related_request', 'related_borrowed_item'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
    )

    def notification_type_badge(self, obj):
        colors = {
            'request_approved': '#059669',
            'request_rejected': '#dc2626',
            'item_issued': '#3b82f6',
            'item_due_soon': '#f59e0b',
            'item_overdue': '#ef4444',
            'extension_approved': '#10b981',
            'extension_rejected': '#dc2626',
            'account_approved': '#6366f1',
            'account_rejected': '#dc2626',
            'new_request': '#8b5cf6',
            'low_stock': '#d97706',
            'system': '#6b7280',
        }
        color = colors.get(obj.notification_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'

    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'Marked {queryset.count()} notifications as read.')

    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'Marked {queryset.count()} notifications as unread.')
