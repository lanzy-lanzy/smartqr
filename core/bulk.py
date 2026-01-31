"""
Bulk Operations Module for Smart Supply

Handles batch processing, CSV imports, and mass operations.
"""
import csv
import io
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction

from .models import (
    Supply, SupplyCategory, EquipmentInstance, SupplyRequest,
    Department, User, AuditLog
)


# =============================================================================
# CSV Export Functions
# =============================================================================

def export_supplies_csv(supplies):
    """Export supplies to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Name', 'Category', 'Quantity', 'Min Stock Level',
        'Unit', 'Is Consumable', 'Default Borrow Days', 'Status', 'Created At'
    ])
    
    for supply in supplies:
        writer.writerow([
            supply.id,
            supply.name,
            supply.category.name,
            supply.quantity,
            supply.min_stock_level,
            supply.unit,
            'Yes' if supply.is_consumable else 'No',
            supply.default_borrow_days,
            supply.stock_status.replace('_', ' ').title(),
            supply.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="supplies_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


def export_equipment_csv(instances):
    """Export equipment instances to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Instance Code', 'Supply Name', 'Serial Number', 'Status',
        'Condition Notes', 'Acquired Date', 'Warranty Expiry',
        'Last Borrowed At', 'Last Borrowed By', 'Active'
    ])
    
    for instance in instances:
        writer.writerow([
            instance.instance_code,
            instance.supply.name,
            instance.serial_number or '',
            instance.get_status_display(),
            instance.condition_notes or '',
            instance.acquired_date.strftime('%Y-%m-%d') if instance.acquired_date else '',
            instance.warranty_expiry.strftime('%Y-%m-%d') if instance.warranty_expiry else '',
            instance.last_borrowed_at.strftime('%Y-%m-%d %H:%M') if instance.last_borrowed_at else '',
            instance.last_borrowed_by.get_full_name() if instance.last_borrowed_by else '',
            'Yes' if instance.is_active else 'No',
        ])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="equipment_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


def export_requests_csv(requests):
    """Export requests to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Request Code', 'Requester', 'Department', 'Supply',
        'Quantity', 'Purpose', 'Priority', 'Status',
        'Requested At', 'Reviewed By', 'Reviewed At', 'Issued At'
    ])
    
    for req in requests:
        writer.writerow([
            req.request_code,
            req.requester.get_full_name(),
            req.requester.department.name if req.requester.department else '',
            req.supply.name,
            req.quantity,
            req.purpose[:100],
            req.get_priority_display(),
            req.get_status_display(),
            req.requested_at.strftime('%Y-%m-%d %H:%M'),
            req.reviewed_by.get_full_name() if req.reviewed_by else '',
            req.reviewed_at.strftime('%Y-%m-%d %H:%M') if req.reviewed_at else '',
            req.issued_at.strftime('%Y-%m-%d %H:%M') if req.issued_at else '',
        ])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="requests_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


def export_borrowed_items_csv(borrowed_items):
    """Export borrowed items to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Request Code', 'Equipment', 'Supply', 'Borrower',
        'Department', 'Borrowed At', 'Return Deadline', 'Returned At',
        'Return Status', 'Days Overdue', 'Notes'
    ])
    
    for item in borrowed_items:
        writer.writerow([
            item.request.request_code,
            item.equipment_instance.instance_code,
            item.equipment_instance.supply.name,
            item.borrower.get_full_name(),
            item.borrower.department.name if item.borrower.department else '',
            item.borrowed_at.strftime('%Y-%m-%d %H:%M'),
            item.return_deadline.strftime('%Y-%m-%d %H:%M'),
            item.returned_at.strftime('%Y-%m-%d %H:%M') if item.returned_at else '',
            item.get_return_status_display(),
            item.overdue_days if item.is_overdue else 0,
            item.return_notes or '',
        ])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="borrowed_items_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    return response


# =============================================================================
# CSV Import Functions
# =============================================================================

def get_csv_template(template_type):
    """Get CSV template for import."""
    templates = {
        'supplies': [
            'Name', 'Category Code', 'Quantity', 'Min Stock Level',
            'Unit', 'Description', 'Default Borrow Days'
        ],
        'equipment': [
            'Supply Name', 'Instance Code', 'Serial Number',
            'Acquired Date (YYYY-MM-DD)', 'Warranty Expiry (YYYY-MM-DD)', 'Condition Notes'
        ],
        'users': [
            'Email', 'First Name', 'Last Name', 'Department Code',
            'Phone', 'Role (department_user/gso_staff/admin)'
        ],
    }
    
    if template_type not in templates:
        return None
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(templates[template_type])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template_type}_import_template.csv"'
    return response


def import_supplies_csv(file_obj, user):
    """
    Import supplies from CSV.
    
    Returns:
        dict: {'success': int, 'errors': list, 'created': list}
    """
    result = {'success': 0, 'errors': [], 'created': []}
    
    try:
        decoded_file = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        
        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Find or validate category
                    category_code = row.get('Category Code', '').strip()
                    try:
                        category = SupplyCategory.objects.get(
                            Q(name__iexact=category_code) | Q(id=category_code)
                        )
                    except SupplyCategory.DoesNotExist:
                        result['errors'].append(f"Row {row_num}: Category '{category_code}' not found")
                        continue
                    
                    # Create supply
                    supply = Supply.objects.create(
                        name=row.get('Name', '').strip(),
                        category=category,
                        quantity=int(row.get('Quantity', 0)),
                        min_stock_level=int(row.get('Min Stock Level', 5)),
                        unit=row.get('Unit', 'pcs').strip(),
                        description=row.get('Description', '').strip(),
                        default_borrow_days=int(row.get('Default Borrow Days', 3)),
                        created_by=user,
                    )
                    
                    result['success'] += 1
                    result['created'].append(supply.name)
                    
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: {str(e)}")
        
        # Log audit
        if result['success'] > 0:
            AuditLog.log(
                user=user,
                action=AuditLog.ActionType.IMPORT,
                entity_type=AuditLog.EntityType.SUPPLY,
                description=f"Imported {result['success']} supplies from CSV",
            )
    
    except Exception as e:
        result['errors'].append(f"File error: {str(e)}")
    
    return result


def import_equipment_csv(file_obj, user):
    """
    Import equipment instances from CSV.
    
    Returns:
        dict: {'success': int, 'errors': list, 'created': list}
    """
    from django.db.models import Q
    
    result = {'success': 0, 'errors': [], 'created': []}
    
    try:
        decoded_file = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        
        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Find supply
                    supply_name = row.get('Supply Name', '').strip()
                    try:
                        supply = Supply.objects.get(name__iexact=supply_name, is_active=True)
                    except Supply.DoesNotExist:
                        result['errors'].append(f"Row {row_num}: Supply '{supply_name}' not found")
                        continue
                    
                    # Parse dates
                    acquired_date = None
                    warranty_expiry = None
                    
                    if row.get('Acquired Date (YYYY-MM-DD)'):
                        try:
                            acquired_date = datetime.strptime(
                                row['Acquired Date (YYYY-MM-DD)'].strip(), '%Y-%m-%d'
                            ).date()
                        except:
                            pass
                    
                    if row.get('Warranty Expiry (YYYY-MM-DD)'):
                        try:
                            warranty_expiry = datetime.strptime(
                                row['Warranty Expiry (YYYY-MM-DD)'].strip(), '%Y-%m-%d'
                            ).date()
                        except:
                            pass
                    
                    # Create instance
                    instance = EquipmentInstance.objects.create(
                        supply=supply,
                        instance_code=row.get('Instance Code', '').strip(),
                        serial_number=row.get('Serial Number', '').strip(),
                        acquired_date=acquired_date,
                        warranty_expiry=warranty_expiry,
                        condition_notes=row.get('Condition Notes', '').strip(),
                    )
                    
                    result['success'] += 1
                    result['created'].append(instance.instance_code)
                    
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: {str(e)}")
        
        # Log audit
        if result['success'] > 0:
            AuditLog.log(
                user=user,
                action=AuditLog.ActionType.IMPORT,
                entity_type=AuditLog.EntityType.INSTANCE,
                description=f"Imported {result['success']} equipment instances from CSV",
            )
    
    except Exception as e:
        result['errors'].append(f"File error: {str(e)}")
    
    return result


# =============================================================================
# Batch Operations
# =============================================================================

def batch_approve_requests(request_ids, user, notes=''):
    """
    Approve multiple requests at once.
    
    Returns:
        dict: {'success': int, 'errors': list}
    """
    result = {'success': 0, 'errors': []}
    
    for req_id in request_ids:
        try:
            supply_request = SupplyRequest.objects.get(
                pk=req_id, 
                status=SupplyRequest.Status.PENDING
            )
            supply_request.approve(user, notes)
            result['success'] += 1
        except SupplyRequest.DoesNotExist:
            result['errors'].append(f"Request {req_id} not found or not pending")
        except Exception as e:
            result['errors'].append(f"Request {req_id}: {str(e)}")
    
    if result['success'] > 0:
        AuditLog.log(
            user=user,
            action=AuditLog.ActionType.APPROVE,
            entity_type=AuditLog.EntityType.REQUEST,
            description=f"Batch approved {result['success']} requests",
        )
    
    return result


def batch_reject_requests(request_ids, user, notes='Batch rejected'):
    """
    Reject multiple requests at once.
    
    Returns:
        dict: {'success': int, 'errors': list}
    """
    result = {'success': 0, 'errors': []}
    
    for req_id in request_ids:
        try:
            supply_request = SupplyRequest.objects.get(
                pk=req_id, 
                status=SupplyRequest.Status.PENDING
            )
            supply_request.reject(user, notes)
            result['success'] += 1
        except SupplyRequest.DoesNotExist:
            result['errors'].append(f"Request {req_id} not found or not pending")
        except Exception as e:
            result['errors'].append(f"Request {req_id}: {str(e)}")
    
    if result['success'] > 0:
        AuditLog.log(
            user=user,
            action=AuditLog.ActionType.REJECT,
            entity_type=AuditLog.EntityType.REQUEST,
            description=f"Batch rejected {result['success']} requests",
        )
    
    return result


def batch_generate_qr_codes(instances, user):
    """
    Generate QR codes for multiple equipment instances.
    
    Returns:
        dict: {'success': int, 'errors': list}
    """
    result = {'success': 0, 'errors': []}
    
    for instance in instances:
        try:
            if instance.generate_qr_code():
                instance.save()
                result['success'] += 1
            else:
                result['errors'].append(f"{instance.instance_code}: QR library not available")
        except Exception as e:
            result['errors'].append(f"{instance.instance_code}: {str(e)}")
    
    if result['success'] > 0:
        AuditLog.log(
            user=user,
            action=AuditLog.ActionType.UPDATE,
            entity_type=AuditLog.EntityType.INSTANCE,
            description=f"Generated QR codes for {result['success']} instances",
        )
    
    return result


def batch_update_stock(updates, user):
    """
    Update stock levels for multiple supplies.
    
    Args:
        updates: list of dicts with 'supply_id' and 'quantity'
        user: User performing the update
    
    Returns:
        dict: {'success': int, 'errors': list}
    """
    from .models import InventoryTransaction
    
    result = {'success': 0, 'errors': []}
    
    with transaction.atomic():
        for update in updates:
            try:
                supply = Supply.objects.get(pk=update['supply_id'])
                old_qty = supply.quantity
                new_qty = update['quantity']
                
                supply.quantity = new_qty
                supply.save()
                
                # Log transaction
                InventoryTransaction.objects.create(
                    supply=supply,
                    transaction_type=InventoryTransaction.TransactionType.ADJUSTMENT,
                    quantity=new_qty - old_qty,
                    previous_quantity=old_qty,
                    new_quantity=new_qty,
                    notes=f"Batch stock update",
                    performed_by=user,
                )
                
                result['success'] += 1
                
            except Supply.DoesNotExist:
                result['errors'].append(f"Supply {update['supply_id']} not found")
            except Exception as e:
                result['errors'].append(f"Supply {update.get('supply_id')}: {str(e)}")
    
    if result['success'] > 0:
        AuditLog.log(
            user=user,
            action=AuditLog.ActionType.UPDATE,
            entity_type=AuditLog.EntityType.SUPPLY,
            description=f"Batch updated stock for {result['success']} supplies",
        )
    
    return result
