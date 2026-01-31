import json
import uuid
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator

from .models import (
    Department, User, SupplyCategory, Supply, EquipmentInstance,
    SupplyRequest, BorrowedItem, QRScanLog, InventoryTransaction,
    RequestorBorrowerAnalytics, StockAdjustment
)


# =============================================================================
# Authentication Views
# =============================================================================

def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.approval_status != User.ApprovalStatus.APPROVED:
                messages.error(request, 'Your account is pending approval. Please wait for an administrator to approve your account.')
                return render(request, 'auth/login.html')
            
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')


def register_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    departments = Department.objects.filter(is_active=True)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone', '')
        department_id = request.POST.get('department')
        
        errors = []
        
        # Validation
        if User.objects.filter(username=username).exists():
            errors.append('An account with this username already exists.')
        
        if email and User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')
        
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if not first_name or not last_name:
            errors.append('First name and last name are required.')
        
        if not username:
            errors.append('Username is required.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'auth/register.html', {
                'departments': departments,
                'form': request.POST
            })
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            department_id=department_id if department_id else None,
            role=User.Role.DEPARTMENT_USER,
            approval_status=User.ApprovalStatus.PENDING
        )
        
        # Create analytics record
        RequestorBorrowerAnalytics.objects.create(user=user)
        
        messages.success(request, 'Account created successfully! Please wait for administrator approval.')
        return redirect('login')
    
    return render(request, 'auth/register.html', {'departments': departments})


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# =============================================================================
# Dashboard Views
# =============================================================================

@login_required
def dashboard(request):
    """Main dashboard view with role-based content."""
    user = request.user
    today = timezone.now()
    
    context = {
        'today': today,
    }
    
    if user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        # GSO/Admin Dashboard
        context.update({
            'pending_requests_count': SupplyRequest.objects.filter(status=SupplyRequest.Status.PENDING).count(),
            'total_supplies': Supply.objects.filter(is_active=True).count(),
            'low_stock_count': Supply.objects.filter(is_active=True, quantity__lte=models.F('min_stock_level')).count(),
            'overdue_items_count': BorrowedItem.objects.filter(
                returned_at__isnull=True,
                return_deadline__lt=today
            ).count(),
            'pending_requests': SupplyRequest.objects.filter(
                status=SupplyRequest.Status.PENDING
            ).select_related('requester', 'supply').order_by('-priority', '-requested_at')[:5],
            'low_stock_items': Supply.objects.filter(
                is_active=True,
                quantity__lte=models.F('min_stock_level')
            )[:6],
            'recent_activity': QRScanLog.objects.select_related('scanned_by').order_by('-scanned_at')[:5],
        })
    else:
        # Department User Dashboard
        context.update({
            'my_pending_requests': SupplyRequest.objects.filter(
                requester=user,
                status=SupplyRequest.Status.PENDING
            ).count(),
            'my_approved_requests': SupplyRequest.objects.filter(
                requester=user,
                status=SupplyRequest.Status.APPROVED
            ).count(),
            'my_active_borrows': BorrowedItem.objects.filter(
                borrower=user,
                returned_at__isnull=True
            ).count(),
            'my_overdue_count': user.overdue_items.count(),
            'my_requests': SupplyRequest.objects.filter(
                requester=user
            ).select_related('supply').order_by('-requested_at')[:5],
            'my_borrowed_items': BorrowedItem.objects.filter(
                borrower=user,
                returned_at__isnull=True
            ).select_related('equipment_instance', 'equipment_instance__supply').order_by('return_deadline')[:5],
        })
    
    return render(request, 'dashboard/index.html', context)


# =============================================================================
# Supply Views
# =============================================================================

@login_required
def supplies_list(request):
    """List all supplies with filtering."""
    category_id = request.GET.get('category')
    search = request.GET.get('search', '')
    stock_status = request.GET.get('stock')
    
    supplies = Supply.objects.filter(is_active=True).select_related('category')
    
    if category_id:
        supplies = supplies.filter(category_id=category_id)
    
    if search:
        supplies = supplies.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    if stock_status == 'low':
        supplies = supplies.filter(quantity__lte=models.F('min_stock_level'), quantity__gt=0)
    elif stock_status == 'out':
        supplies = supplies.filter(quantity=0)
    elif stock_status == 'available':
        supplies = supplies.filter(quantity__gt=models.F('min_stock_level'))
    
    categories = SupplyCategory.objects.filter(is_active=True)
    
    paginator = Paginator(supplies, 12)
    page = request.GET.get('page', 1)
    supplies = paginator.get_page(page)
    
    context = {
        'supplies': supplies,
        'categories': categories,
        'current_category': category_id,
        'search': search,
        'stock_status': stock_status,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'partials/supply_grid.html', context)
    
    return render(request, 'supplies/list.html', context)


@login_required
def supply_detail(request, pk):
    """Supply detail view (modal-ready)."""
    supply = get_object_or_404(Supply, pk=pk, is_active=True)
    instances = supply.instances.filter(is_active=True) if not supply.is_consumable else None
    
    context = {
        'supply': supply,
        'instances': instances,
    }
    
    return render(request, 'supplies/detail.html', context)


@login_required
def equipment_list(request):
    """List equipment instances."""
    status = request.GET.get('status')
    search = request.GET.get('search', '')
    
    instances = EquipmentInstance.objects.filter(is_active=True).select_related('supply', 'supply__category')
    
    if status:
        instances = instances.filter(status=status)
    
    if search:
        instances = instances.filter(
            Q(instance_code__icontains=search) | 
            Q(serial_number__icontains=search) |
            Q(supply__name__icontains=search)
        )
    
    paginator = Paginator(instances, 20)
    page = request.GET.get('page', 1)
    instances = paginator.get_page(page)
    
    context = {
        'instances': instances,
        'current_status': status,
        'search': search,
        'status_choices': EquipmentInstance.Status.choices,
    }
    
    return render(request, 'supplies/equipment.html', context)


@login_required
def equipment_detail(request, pk):
    """Equipment instance detail view (modal-ready)."""
    instance = get_object_or_404(EquipmentInstance, pk=pk, is_active=True)
    
    context = {
        'instance': instance,
    }
    
    return render(request, 'supplies/equipment_detail.html', context)


@login_required
def equipment_qr(request, pk):
    """Equipment instance QR code view."""
    instance = get_object_or_404(EquipmentInstance, pk=pk, is_active=True)
    
    context = {
        'instance': instance,
    }
    
    return render(request, 'supplies/equipment_qr.html', context)


@login_required  
def categories_list(request):
    """List supply categories."""
    categories = SupplyCategory.objects.filter(is_active=True).annotate(
        supply_count=Count('supplies', filter=Q(supplies__is_active=True))
    )
    
    return render(request, 'supplies/categories.html', {'categories': categories})


# =============================================================================
# Request Views
# =============================================================================

@login_required
def request_create(request):
    """Create new supply request."""
    from .models import Notification
    
    if request.user.has_overdue_items:
        messages.error(request, 'You have overdue items. Please return them before making new requests.')
        return redirect('my_requests')
    
    # Handle instance query parameter for pre-selecting equipment
    preselected_instance_id = request.GET.get('instance')
    preselected_supply_id = request.GET.get('supply')
    
    if request.method == 'POST':
        supply_id = request.POST.get('supply_id')
        quantity = int(request.POST.get('quantity', 1))
        purpose = request.POST.get('purpose')
        priority = request.POST.get('priority', 'normal')
        needed_by = request.POST.get('needed_by')
        instance_id = request.POST.get('instance_id')  # Optional specific instance
        
        supply = get_object_or_404(Supply, pk=supply_id, is_active=True)
        
        # Create request
        supply_request = SupplyRequest.objects.create(
            requester=request.user,
            supply=supply,
            quantity=quantity,
            purpose=purpose,
            priority=priority,
            needed_by=needed_by if needed_by else None,
            requested_instance_id=instance_id if instance_id else None,
        )
        
        # Update user analytics
        analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=request.user)
        analytics.total_requests += 1
        analytics.last_request_at = timezone.now()
        analytics.save()
        
        # Notify GSO staff about new request
        Notification.notify_new_request_to_gso(supply_request)
        
        messages.success(request, f'Request {supply_request.request_code} submitted successfully!')
        
        if request.headers.get('HX-Request'):
            return render(request, 'partials/request_success.html', {'request': supply_request})
        
        return redirect('my_requests')
    
    supplies = Supply.objects.filter(is_active=True, quantity__gt=0).select_related('category')
    categories = SupplyCategory.objects.filter(is_active=True)
    
    # Handle preselected instance from equipment list
    preselected_instance = None
    preselected_supply = None
    
    if preselected_instance_id:
        preselected_instance = get_object_or_404(EquipmentInstance, pk=preselected_instance_id, is_active=True)
        preselected_supply = preselected_instance.supply
    elif preselected_supply_id:
        preselected_supply = get_object_or_404(Supply, pk=preselected_supply_id, is_active=True)
    
    context = {
        'supplies': supplies,
        'categories': categories,
        'priority_choices': SupplyRequest.Priority.choices,
        'preselected_supply': preselected_supply,
        'preselected_instance': preselected_instance,
    }
    
    return render(request, 'requests/create.html', context)


@login_required
def my_requests(request):
    """List user's own requests."""
    status_filter = request.GET.get('status')
    
    requests_qs = SupplyRequest.objects.filter(
        requester=request.user
    ).select_related('supply', 'reviewed_by').order_by('-requested_at')
    
    if status_filter:
        if status_filter == 'overdue':
            # Get requests with overdue borrowed items
            overdue_request_ids = BorrowedItem.objects.filter(
                borrower=request.user,
                returned_at__isnull=True,
                return_deadline__lt=timezone.now()
            ).values_list('request_id', flat=True)
            requests_qs = requests_qs.filter(id__in=overdue_request_ids)
        else:
            requests_qs = requests_qs.filter(status=status_filter)
    
    paginator = Paginator(requests_qs, 50) # Use larger page size for easier grouping logic if needed, or group after pagination
    page = request.GET.get('page', 1)
    requests_page = paginator.get_page(page)
    
    # Group the requests for the current page
    grouped_requests = []
    seen_batches = set()
    
    for req in requests_page:
        if req.batch_group_id:
            if req.batch_group_id not in seen_batches:
                batch_items = SupplyRequest.objects.filter(batch_group_id=req.batch_group_id).select_related('supply')
                req.is_batch = True
                req.batch_items = batch_items
                req.batch_item_count = batch_items.count()
                
                # Calculate returned count for the batch
                borrowed_items = BorrowedItem.objects.filter(request__batch_group_id=req.batch_group_id)
                req.batch_returned_count = borrowed_items.filter(returned_at__isnull=False).count()
                
                grouped_requests.append(req)
                seen_batches.add(req.batch_group_id)
        else:
            req.is_batch = False
            grouped_requests.append(req)
    
    context = {
        'requests': grouped_requests,
        'page_obj': requests_page,
        'current_status': status_filter,
        'status_choices': SupplyRequest.Status.choices,
    }
    
    return render(request, 'requests/my_requests.html', context)


@login_required
def request_detail(request, pk):
    """Request detail view."""
    supply_request = get_object_or_404(SupplyRequest, pk=pk)
    
    # Check access
    if supply_request.requester != request.user and request.user.role == User.Role.DEPARTMENT_USER:
        messages.error(request, 'You do not have permission to view this request.')
        return redirect('my_requests')
    
    borrowed_items = supply_request.borrowed_items.select_related('equipment_instance')
    
    context = {
        'request': supply_request,
        'borrowed_items': borrowed_items,
    }
    
    return render(request, 'requests/detail.html', context)


@login_required
def request_qr(request, pk):
    """Show QR code for a request."""
    supply_request = get_object_or_404(SupplyRequest, pk=pk)
    
    if not supply_request.qr_code:
        supply_request.generate_qr_code()
        supply_request.save()
    
    return render(request, 'requests/qr_modal.html', {'request': supply_request})


# =============================================================================
# GSO Staff Views
# =============================================================================

@login_required
def pending_requests(request):
    """List pending requests for GSO staff."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    priority = request.GET.get('priority')
    department = request.GET.get('department')
    
    requests_qs = SupplyRequest.objects.filter(
        status=SupplyRequest.Status.PENDING
    ).select_related('requester', 'supply', 'requester__department').order_by('-priority', '-requested_at')
    
    if priority:
        requests_qs = requests_qs.filter(priority=priority)
    
    grouped_requests = []
    seen_batches = set()
    
    for req in requests_qs:
        if req.batch_group_id:
            if req.batch_group_id not in seen_batches:
                batch_items = SupplyRequest.objects.filter(batch_group_id=req.batch_group_id).select_related('supply', 'requester', 'requester__department')
                req.is_batch = True
                req.batch_items = batch_items
                req.batch_item_count = batch_items.count()
                grouped_requests.append(req)
                seen_batches.add(req.batch_group_id)
        else:
            req.is_batch = False
            grouped_requests.append(req)
            
    departments = Department.objects.filter(is_active=True)
    
    context = {
        'requests': grouped_requests,
        'departments': departments,
        'priority_choices': SupplyRequest.Priority.choices,
        'current_priority': priority,
        'current_department': department,
    }
    
    return render(request, 'requests/pending.html', context)


@login_required
@require_POST
def approve_request(request, pk):
    """Approve a pending request."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    supply_request = get_object_or_404(SupplyRequest, pk=pk, status=SupplyRequest.Status.PENDING)
    notes = request.POST.get('notes', '')
    
    supply_request.approve(request.user, notes)
    
    # Update requester analytics
    analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=supply_request.requester)
    analytics.approved_requests += 1
    analytics.save()
    
    # Send notification to requester
    Notification.notify_request_approved(supply_request)
    
    if request.headers.get('HX-Request'):
        response = render(request, 'partials/request_approved.html', {'request': supply_request})
        response['HX-Trigger'] = json.dumps({'closeModal': True, 'refreshRequests': True})
        return response
    
    messages.success(request, f'Request {supply_request.request_code} approved.')
    return redirect('pending_requests')


@login_required
@require_POST
def reject_request(request, pk):
    """Reject a pending request."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    supply_request = get_object_or_404(SupplyRequest, pk=pk, status=SupplyRequest.Status.PENDING)
    notes = request.POST.get('notes', 'Request rejected.')
    
    supply_request.reject(request.user, notes)
    
    # Update requester analytics
    analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=supply_request.requester)
    analytics.rejected_requests += 1
    analytics.save()
    
    # Send notification to requester
    Notification.notify_request_rejected(supply_request)
    
    if request.headers.get('HX-Request'):
        response = render(request, 'partials/request_rejected.html', {'request': supply_request})
        response['HX-Trigger'] = json.dumps({'closeModal': True, 'refreshRequests': True})
        return response
    
    messages.success(request, f'Request {supply_request.request_code} rejected.')
    return redirect('pending_requests')


# =============================================================================
# QR Scanner & Borrowing Views
# =============================================================================

@login_required
def qr_scanner(request):
    """QR scanner interface."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    return render(request, 'scanner/index.html')


@login_required
@require_POST
def process_qr_scan(request):
    """Process a QR code scan."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    qr_data = request.POST.get('qr_data', '')
    scan_type = request.POST.get('scan_type', 'scan')
    
    # Log the scan
    scan_log = QRScanLog.objects.create(
        scanned_by=request.user,
        qr_data=qr_data,
        scan_type=scan_type,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    
    result = {'success': False, 'message': 'Unknown QR code format'}
    
    try:
        if qr_data.startswith('INSTANCE-'):
            # Equipment instance scan
            instance_id = qr_data.split('-')[1]
            instance = EquipmentInstance.objects.get(id=instance_id)
            scan_log.equipment_instance = instance
            scan_log.save()
            
            data = {
                'id': instance.id,
                'code': instance.instance_code,
                'supply': instance.supply.name,
                'supply_id': instance.supply.id,
                'status': instance.status,
                'current_borrower': instance.current_borrower.get_full_name() if instance.current_borrower else None,
                'is_overdue': instance.borrowed_items.filter(returned_at__isnull=True, return_deadline__lt=timezone.now()).exists() if instance.status == EquipmentInstance.Status.BORROWED else False,
            }

            # If instance is available, look for pending approved requests for this supply
            if instance.status == EquipmentInstance.Status.AVAILABLE:
                pending_requests = SupplyRequest.objects.filter(
                    supply=instance.supply,
                    status=SupplyRequest.Status.APPROVED
                ).select_related('requester')
                
                if pending_requests.exists():
                    data['pending_approvals'] = [
                        {
                            'id': r.id,
                            'code': r.request_code,
                            'requester': r.requester.get_full_name(),
                            'supply': r.supply.name,
                            'supply_id': r.supply.id,
                            'quantity': r.quantity,
                            'status': r.status,
                            'is_consumable': r.supply.is_consumable,
                        } for r in pending_requests
                    ]

            result = {
                'success': True,
                'type': 'instance',
                'data': data
            }
            
        elif qr_data.startswith('BORROW-BATCH-'):
            # Batch request scan
            batch_id = qr_data.replace('BORROW-BATCH-', '')
            requests = SupplyRequest.objects.filter(batch_group_id=batch_id)
            
            result = {
                'success': True,
                'type': 'batch',
                'data': {
                    'batch_id': batch_id,
                    'requests': [
                        {
                            'id': r.id,
                            'code': r.request_code,
                            'supply': r.supply.name,
                            'quantity': r.quantity,
                            'status': r.status,
                            'instance_id': r.borrowed_items.filter(returned_at__isnull=True).first().equipment_instance.id if r.status == 'issued' and r.borrowed_items.filter(returned_at__isnull=True).exists() else None,
                            'instance_code': r.borrowed_items.filter(returned_at__isnull=True).first().equipment_instance.instance_code if r.status == 'issued' and r.borrowed_items.filter(returned_at__isnull=True).exists() else None,
                        }
                        for r in requests
                    ]
                }
            }
            
        elif qr_data.startswith('BORROW-'):
            # Individual request scan
            # Format: BORROW-{id}-{requester_id}-{supply_id}
            # Extract ID by removing prefix and taking first part
            request_id = qr_data.replace('BORROW-', '').split('-')[0]
            supply_request = SupplyRequest.objects.get(id=request_id)
            scan_log.supply_request = supply_request
            scan_log.save()
            
            data = {
                'id': supply_request.id,
                'code': supply_request.request_code,
                'requester': supply_request.requester.get_full_name(),
                'supply': supply_request.supply.name,
                'supply_id': supply_request.supply.id,
                'quantity': supply_request.quantity,
                'status': supply_request.status,
                'priority': supply_request.priority,
                'is_consumable': supply_request.supply.is_consumable,
                'requested_instance_id': supply_request.requested_instance.id if supply_request.requested_instance else None,
                'requested_instance_code': supply_request.requested_instance.instance_code if supply_request.requested_instance else None,
            }
            
            # If status is issued, include borrowed item info for return flow
            if supply_request.status == SupplyRequest.Status.ISSUED:
                active_borrow = supply_request.borrowed_items.filter(returned_at__isnull=True).first()
                if active_borrow:
                    data['borrowed_item_id'] = active_borrow.id
                    data['instance_id'] = active_borrow.equipment_instance.id
                    data['instance_code'] = active_borrow.equipment_instance.instance_code

            result = {
                'success': True,
                'type': 'request',
                'data': data
            }
            
        elif qr_data.startswith('SUPPLY-'):
            # Supply scan
            parts = qr_data.split('-')
            supply_id = parts[1]
            supply = Supply.objects.get(id=supply_id)
            scan_log.supply = supply
            scan_log.save()
            
            result = {
                'success': True,
                'type': 'supply',
                'data': {
                    'id': supply.id,
                    'name': supply.name,
                    'quantity': supply.quantity,
                    'available': supply.available_quantity,
                    'status': supply.stock_status,
                }
            }
        
        scan_log.was_successful = result['success']
        scan_log.save()
        
    except Exception as e:
        scan_log.was_successful = False
        scan_log.error_message = str(e)
        scan_log.save()
        result = {'success': False, 'message': str(e)}
    
    return JsonResponse(result)


@login_required
@require_POST
def issue_item(request):
    """Issue an item to fulfill a request."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    request_id = request.POST.get('request_id')
    instance_id = request.POST.get('instance_id')
    
    supply_request = get_object_or_404(SupplyRequest, pk=request_id, status=SupplyRequest.Status.APPROVED)
    
    # Handle Consumables
    if supply_request.supply.is_consumable:
        supply = supply_request.supply
        if supply.quantity < supply_request.quantity:
            return JsonResponse({'success': False, 'error': f'Insufficient quantity for {supply.name}'}, status=400)
        
        previous_qty = supply.quantity
        supply.quantity -= supply_request.quantity
        supply.save()

        # Update request status
        supply_request.status = SupplyRequest.Status.ISSUED
        supply_request.issued_by = request.user
        supply_request.issued_at = timezone.now()
        supply_request.save()

        # Log transaction
        InventoryTransaction.objects.create(
            supply=supply,
            transaction_type=InventoryTransaction.TransactionType.OUT,
            quantity=-supply_request.quantity,
            previous_quantity=previous_qty,
            new_quantity=supply.quantity,
            reference_code=supply_request.request_code,
            supply_request=supply_request,
            performed_by=request.user,
        )

        # Log scan (if request QR was scanned)
        QRScanLog.objects.create(
            scanned_by=request.user,
            qr_data=supply_request.qr_data,
            scan_type=QRScanLog.ScanType.ISSUE,
            supply_request=supply_request,
            was_successful=True,
        )

        # If HTMX/Unpoly, redirect
        if request.headers.get('HX-Request') or request.headers.get('X-Up-Target'):
            target_url = reverse('batch_request_detail', args=[supply_request.batch_group_id]) if supply_request.batch_group_id else reverse('request_detail', args=[supply_request.id])
            response = HttpResponse('')
            response['HX-Redirect'] = target_url
            response['X-Up-Location'] = target_url
            return response

        return JsonResponse({
            'success': True,
            'message': f'Issued {supply_request.quantity} {supply.name}(s) to {supply_request.requester.get_full_name()}'
        })

    # Handle Equipment (Existing Logic)
    instance = get_object_or_404(EquipmentInstance, pk=instance_id, status=EquipmentInstance.Status.AVAILABLE)
    
    # Create borrowed item
    borrowed_item = BorrowedItem.objects.create(
        request=supply_request,
        equipment_instance=instance,
        borrower=supply_request.requester,
        return_deadline=timezone.now() + timedelta(days=supply_request.supply.default_borrow_days)
    )
    
    # Update instance status
    instance.status = EquipmentInstance.Status.BORROWED
    instance.last_borrowed_by = supply_request.requester
    instance.last_borrowed_at = timezone.now()
    instance.save()
    
    # Update request status
    supply_request.status = SupplyRequest.Status.ISSUED
    supply_request.issued_by = request.user
    supply_request.issued_at = timezone.now()
    supply_request.save()
    
    # Log transaction
    InventoryTransaction.objects.create(
        supply=supply_request.supply,
        equipment_instance=instance,
        transaction_type=InventoryTransaction.TransactionType.OUT,
        quantity=-1,
        previous_quantity=supply_request.supply.quantity,
        new_quantity=supply_request.supply.quantity,
        reference_code=supply_request.request_code,
        supply_request=supply_request,
        borrowed_item=borrowed_item,
        performed_by=request.user,
    )
    
    # Log scan
    QRScanLog.objects.create(
        scanned_by=request.user,
        qr_data=instance.qr_data,
        scan_type=QRScanLog.ScanType.ISSUE,
        equipment_instance=instance,
        supply_request=supply_request,
        was_successful=True,
    )
    
    # Update borrower analytics
    analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=supply_request.requester)
    analytics.update_from_borrow(borrowed_item)
    
    # Send notification to borrower
    Notification.notify_item_issued(borrowed_item)
    
    # If it's an HTMX or Unpoly request, we can either redirect or return success
    if request.headers.get('HX-Request') or request.headers.get('X-Up-Target'):
        if supply_request.batch_group_id:
            response = HttpResponse('')
            response['HX-Redirect'] = reverse('batch_request_detail', args=[supply_request.batch_group_id])
            response['X-Up-Location'] = reverse('batch_request_detail', args=[supply_request.batch_group_id])
            return response
        else:
            response = HttpResponse('')
            response['HX-Redirect'] = reverse('request_detail', args=[supply_request.id])
            response['X-Up-Location'] = reverse('request_detail', args=[supply_request.id])
            return response

    return JsonResponse({
        'success': True,
        'message': f'Item {instance.instance_code} issued to {supply_request.requester.get_full_name()}',
        'borrowed_item_id': borrowed_item.id,
    })


@login_required
def returns_list(request):
    """List items that need to be returned."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    filter_type = request.GET.get('filter', 'all')
    
    if filter_type == 'history':
        returned_items = BorrowedItem.objects.filter(
            returned_at__isnull=False
        ).select_related(
            'equipment_instance', 'equipment_instance__supply', 'borrower', 'request'
        ).order_by('-returned_at')
        
        # Categorize by condition for history view
        categorized = {
            'good': returned_items.filter(return_status='good'),
            'damaged': returned_items.filter(return_status='damaged'),
            'lost': returned_items.filter(return_status='lost')
        }
        
        context = {
            'returned_items': returned_items,
            'categorized': categorized,
            'current_filter': filter_type,
        }
    else:
        borrowed_items = BorrowedItem.objects.filter(
            returned_at__isnull=True
        ).select_related(
            'equipment_instance', 'equipment_instance__supply', 'borrower', 'request'
        ).order_by('return_deadline')
        
        if filter_type == 'overdue':
            borrowed_items = borrowed_items.filter(return_deadline__lt=timezone.now())
        elif filter_type == 'due_soon':
            borrowed_items = borrowed_items.filter(
                return_deadline__gte=timezone.now(),
                return_deadline__lte=timezone.now() + timedelta(days=2)
            )
        
        context = {
            'borrowed_items': borrowed_items,
            'current_filter': filter_type,
        }
    
    return render(request, 'requests/returns.html', context)


@login_required
@require_POST
def process_return(request):
    """Process item return."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    borrowed_item_id = request.POST.get('borrowed_item_id')
    instance_id = request.POST.get('instance_id')
    return_status = request.POST.get('return_status', 'good')
    notes = request.POST.get('notes', '')
    
    if borrowed_item_id:
        borrowed_item = get_object_or_404(BorrowedItem, pk=borrowed_item_id, returned_at__isnull=True)
    elif instance_id:
        # For scanner: find the active borrow for this instance
        borrowed_item = get_object_or_404(BorrowedItem, equipment_instance_id=instance_id, returned_at__isnull=True)
    else:
        return JsonResponse({'error': 'No item specified'}, status=400)
    
    # Process the return
    borrowed_item.process_return(request.user, return_status, notes)
    
    # Update analytics
    analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=borrowed_item.borrower)
    analytics.update_from_return(borrowed_item)
    
    # Log transaction
    InventoryTransaction.objects.create(
        supply=borrowed_item.equipment_instance.supply,
        equipment_instance=borrowed_item.equipment_instance,
        transaction_type=InventoryTransaction.TransactionType.RETURN,
        quantity=1,
        previous_quantity=borrowed_item.equipment_instance.supply.quantity,
        new_quantity=borrowed_item.equipment_instance.supply.quantity,
        reference_code=borrowed_item.request.request_code,
        supply_request=borrowed_item.request,
        borrowed_item=borrowed_item,
        notes=f'Returned: {return_status}. {notes}',
        performed_by=request.user,
    )
    
    # Log scan
    QRScanLog.objects.create(
        scanned_by=request.user,
        qr_data=borrowed_item.equipment_instance.qr_data,
        scan_type=QRScanLog.ScanType.RETURN,
        equipment_instance=borrowed_item.equipment_instance,
        supply_request=borrowed_item.request,
        was_successful=True,
        notes=notes,
    )
    
    # Handle damage/loss
    if return_status in ['damaged', 'lost']:
        StockAdjustment.objects.create(
            supply=borrowed_item.equipment_instance.supply,
            equipment_instance=borrowed_item.equipment_instance,
            reason=StockAdjustment.AdjustmentReason.DAMAGE if return_status == 'damaged' else StockAdjustment.AdjustmentReason.LOSS,
            quantity=-1,
            description=notes or f'Item {return_status} upon return',
            is_penalty=True,
            responsible_user=borrowed_item.borrower,
            borrowed_item=borrowed_item,
            adjusted_by=request.user,
        )
    
    response_data = {
        'success': True,
        'message': f'Return processed for {borrowed_item.equipment_instance.instance_code}',
    }
    
    response = JsonResponse(response_data)
    # If it's an HTMX request from the returns list, redirect to history
    if request.headers.get('HX-Request') == 'true':
        response['HX-Redirect'] = reverse('returns') + '?filter=history'
        
    return response


# =============================================================================
# Admin Views
# =============================================================================

@login_required
def users_list(request):
    """List users (admin only)."""
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    status = request.GET.get('status')
    role = request.GET.get('role')
    
    users = User.objects.select_related('department').order_by('-created_at')
    
    if status:
        users = users.filter(approval_status=status)
    
    if role:
        users = users.filter(role=role)
    
    context = {
        'users': users,
        'status_choices': User.ApprovalStatus.choices,
        'role_choices': User.Role.choices,
        'current_status': status,
        'current_role': role,
    }
    
    return render(request, 'admin/users.html', context)


@login_required
@require_POST
def approve_user(request, pk):
    """Approve a pending user."""
    from .models import Notification
    
    if request.user.role != User.Role.ADMIN:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = get_object_or_404(User, pk=pk, approval_status=User.ApprovalStatus.PENDING)
    user.approval_status = User.ApprovalStatus.APPROVED
    user.save()
    
    # Send notification to the approved user
    Notification.notify_account_approved(user)
    
    messages.success(request, f'User {user.get_full_name()} approved.')
    
    if request.headers.get('HX-Request'):
        return HttpResponse('<span class="badge-success">Approved</span>')
    
    return redirect('users')


@login_required
def departments_list(request):
    """List departments (admin only)."""
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    departments = Department.objects.annotate(
        user_count=Count('users')
    ).order_by('name')
    
    return render(request, 'admin/departments.html', {'departments': departments})


@login_required
def analytics_view(request):
    """Analytics dashboard (admin only)."""
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    # Get various analytics
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(approval_status=User.ApprovalStatus.APPROVED).count(),
        'total_supplies': Supply.objects.filter(is_active=True).count(),
        'total_requests': SupplyRequest.objects.count(),
        'total_borrows': BorrowedItem.objects.count(),
        'overdue_items': BorrowedItem.objects.filter(
            returned_at__isnull=True,
            return_deadline__lt=timezone.now()
        ).count(),
        'top_borrowers': RequestorBorrowerAnalytics.objects.select_related('user').order_by('-total_borrows')[:10],
        'low_reliability_users': RequestorBorrowerAnalytics.objects.filter(reliability_score__lt=70).select_related('user')[:10],
    }
    
    return render(request, 'admin/analytics.html', context)


# =============================================================================
# API Endpoints
# =============================================================================

@login_required
@require_GET
def api_supplies_search(request):
    """Search supplies API for autocomplete."""
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    
    supplies = Supply.objects.filter(
        is_active=True,
        name__icontains=query
    ).select_related('category')[:20]
    
    if category:
        supplies = supplies.filter(category_id=category)
    
    data = [
        {
            'id': s.id,
            'name': s.name,
            'category': s.category.name,
            'available': s.available_quantity,
            'unit': s.unit,
            'is_consumable': s.is_consumable,
        }
        for s in supplies
    ]
    
    return JsonResponse({'results': data})


@login_required
@require_GET
def api_instances_for_supply(request, supply_id):
    """Get available instances for a supply."""
    supply = get_object_or_404(Supply, pk=supply_id)
    
    instances = supply.instances.filter(
        is_active=True,
        status=EquipmentInstance.Status.AVAILABLE
    )
    
    data = [
        {
            'id': i.id,
            'code': i.instance_code,
            'serial': i.serial_number,
        }
        for i in instances
    ]
    
    return JsonResponse({'instances': data})


# Import models at the top level to avoid issues
from django.db import models


# =============================================================================
# Extension Requests
# =============================================================================

@login_required
def request_extension(request, borrowed_item_id):
    """Request a deadline extension."""
    from .models import ExtensionRequest
    
    borrowed_item = get_object_or_404(BorrowedItem, pk=borrowed_item_id, returned_at__isnull=True)
    
    # Verify ownership
    if borrowed_item.borrower != request.user:
        messages.error(request, 'You can only request extensions for your own borrowed items.')
        return redirect('my_requests')
    
    if request.method == 'POST':
        days = int(request.POST.get('days', 3))
        reason = request.POST.get('reason', '')
        
        extension = ExtensionRequest.objects.create(
            borrowed_item=borrowed_item,
            requested_days=days,
            reason=reason,
            original_deadline=borrowed_item.return_deadline,
            requested_by=request.user,
        )
        
        messages.success(request, 'Extension request submitted successfully.')
        return redirect('my_requests')
    
    return render(request, 'requests/extension_form.html', {'borrowed_item': borrowed_item})


@login_required
def extensions_list(request):
    """List extension requests (GSO Staff)."""
    from .models import ExtensionRequest
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    extensions = ExtensionRequest.objects.filter(
        status=ExtensionRequest.Status.PENDING
    ).select_related('borrowed_item', 'borrowed_item__equipment_instance', 'requested_by')
    
    return render(request, 'requests/extensions.html', {'extensions': extensions})


@login_required
@require_POST
def approve_extension(request, pk):
    """Approve extension request."""
    from .models import ExtensionRequest, AuditLog, Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    extension = get_object_or_404(ExtensionRequest, pk=pk, status=ExtensionRequest.Status.PENDING)
    notes = request.POST.get('notes', '')
    
    extension.approve(request.user, notes)
    
    AuditLog.log(
        user=request.user,
        action=AuditLog.ActionType.APPROVE,
        entity_type=AuditLog.EntityType.EXTENSION,
        description=f"Approved extension for {extension.borrowed_item}",
        entity_id=extension.id,
        request=request
    )
    
    # Send notification to requester
    Notification.notify_extension_approved(extension)
    
    messages.success(request, 'Extension approved.')
    return redirect('extensions')


@login_required
@require_POST
def reject_extension(request, pk):
    """Reject extension request."""
    from .models import ExtensionRequest, AuditLog, Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    extension = get_object_or_404(ExtensionRequest, pk=pk, status=ExtensionRequest.Status.PENDING)
    notes = request.POST.get('notes', 'Extension rejected')
    
    extension.reject(request.user, notes)
    
    AuditLog.log(
        user=request.user,
        action=AuditLog.ActionType.REJECT,
        entity_type=AuditLog.EntityType.EXTENSION,
        description=f"Rejected extension for {extension.borrowed_item}",
        entity_id=extension.id,
        request=request
    )
    
    # Send notification to requester
    Notification.notify_extension_rejected(extension)
    
    messages.success(request, 'Extension rejected.')
    return redirect('extensions')


# =============================================================================
# Batch Operations
# =============================================================================

@login_required
@require_POST
def batch_approve_requests_view(request):
    """Batch approve multiple requests."""
    from .bulk import batch_approve_requests
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    request_ids = request.POST.getlist('request_ids')
    notes = request.POST.get('notes', '')
    
    result = batch_approve_requests(request_ids, request.user, notes)
    
    messages.success(request, f"Approved {result['success']} requests.")
    if result['errors']:
        messages.warning(request, f"Errors: {', '.join(result['errors'][:3])}")
    
    return redirect('pending_requests')


@login_required
@require_POST
def batch_reject_requests_view(request):
    """Batch reject multiple requests."""
    from .bulk import batch_reject_requests
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    request_ids = request.POST.getlist('request_ids')
    notes = request.POST.get('notes', 'Batch rejected')
    
    result = batch_reject_requests(request_ids, request.user, notes)
    
    messages.success(request, f"Rejected {result['success']} requests.")
    return redirect('pending_requests')


# =============================================================================
# Audit Log
# =============================================================================

@login_required
def audit_log_view(request):
    """View audit log (admin only)."""
    from .models import AuditLog
    
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    logs = AuditLog.objects.select_related('user').order_by('-created_at')
    
    # Filters
    action = request.GET.get('action')
    if action:
        logs = logs.filter(action=action)
    
    entity_type = request.GET.get('entity_type')
    if entity_type:
        logs = logs.filter(entity_type=entity_type)
    
    user_id = request.GET.get('user')
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'action_choices': AuditLog.ActionType.choices,
        'entity_choices': AuditLog.EntityType.choices,
        'current_action': action,
        'current_entity': entity_type,
    }
    
    return render(request, 'admin/audit_log.html', context)


# =============================================================================
# Reports & Export
# =============================================================================

@login_required
def report_inventory(request):
    """Generate inventory PDF report."""
    from .reports import generate_inventory_report
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    supplies = Supply.objects.filter(is_active=True).select_related('category').order_by('category', 'name')
    return generate_inventory_report(supplies)


@login_required
def report_borrowing(request):
    """Generate borrowing history PDF report."""
    from .reports import generate_borrowing_report
    
    if request.user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        borrowed_items = BorrowedItem.objects.select_related(
            'equipment_instance', 'borrower', 'request'
        ).order_by('-borrowed_at')
    else:
        borrowed_items = BorrowedItem.objects.filter(
            borrower=request.user
        ).select_related('equipment_instance', 'request').order_by('-borrowed_at')
    
    return generate_borrowing_report(borrowed_items, user=request.user)


@login_required
def report_analytics(request):
    """Generate user analytics PDF report."""
    from .reports import generate_user_analytics_report
    
    if request.user.role != User.Role.ADMIN:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    analytics = RequestorBorrowerAnalytics.objects.select_related('user', 'user__department').order_by('-reliability_score')
    return generate_user_analytics_report(analytics)


@login_required
def report_qr_sheet(request):
    """Generate QR code sheet PDF."""
    from .reports import generate_qr_sheet
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    supply_id = request.GET.get('supply')
    if supply_id:
        instances = EquipmentInstance.objects.filter(supply_id=supply_id, is_active=True)
    else:
        instances = EquipmentInstance.objects.filter(is_active=True).select_related('supply')
    
    return generate_qr_sheet(instances)


# =============================================================================
# CSV Export
# =============================================================================

@login_required
def export_supplies(request):
    """Export supplies to CSV."""
    from .bulk import export_supplies_csv
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    supplies = Supply.objects.filter(is_active=True).select_related('category')
    return export_supplies_csv(supplies)


@login_required
def export_equipment(request):
    """Export equipment to CSV."""
    from .bulk import export_equipment_csv
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    instances = EquipmentInstance.objects.filter(is_active=True).select_related('supply', 'last_borrowed_by')
    return export_equipment_csv(instances)


@login_required
def export_requests(request):
    """Export requests to CSV."""
    from .bulk import export_requests_csv
    
    if request.user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        requests_qs = SupplyRequest.objects.select_related('supply', 'requester', 'requester__department', 'reviewed_by')
    else:
        requests_qs = SupplyRequest.objects.filter(requester=request.user).select_related('supply', 'reviewed_by')
    
    return export_requests_csv(requests_qs)


@login_required
def export_borrowed(request):
    """Export borrowed items to CSV."""
    from .bulk import export_borrowed_items_csv
    
    if request.user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        items = BorrowedItem.objects.select_related(
            'equipment_instance', 'equipment_instance__supply', 'borrower', 'borrower__department', 'request'
        )
    else:
        items = BorrowedItem.objects.filter(borrower=request.user).select_related(
            'equipment_instance', 'equipment_instance__supply', 'request'
        )
    
    return export_borrowed_items_csv(items)


# =============================================================================
# CSV Import
# =============================================================================

@login_required
def import_view(request):
    """Handle CSV imports."""
    from .bulk import import_supplies_csv, import_equipment_csv
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        import_type = request.POST.get('import_type')
        file = request.FILES.get('file')
        
        if not file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('import')
        
        if import_type == 'supplies':
            result = import_supplies_csv(file, request.user)
        elif import_type == 'equipment':
            result = import_equipment_csv(file, request.user)
        else:
            messages.error(request, 'Invalid import type.')
            return redirect('import')
        
        if result['success'] > 0:
            messages.success(request, f"Successfully imported {result['success']} records.")
        if result['errors']:
            for error in result['errors'][:5]:
                messages.warning(request, error)
        
        return redirect('import')
    
    return render(request, 'admin/import.html')


@login_required
def import_template(request, template_type):
    """Download CSV import template."""
    from .bulk import get_csv_template
    
    response = get_csv_template(template_type)
    if response:
        return response
    
    messages.error(request, 'Invalid template type.')
    return redirect('import')


# =============================================================================
# Chart Data API
# =============================================================================

@login_required
@require_GET
def api_chart_data(request):
    """Get data for dashboard charts."""
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    
    chart_type = request.GET.get('type', 'requests')
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    if chart_type == 'requests':
        # Requests over time
        data = SupplyRequest.objects.filter(
            requested_at__gte=start_date
        ).annotate(
            date=TruncDate('requested_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return JsonResponse({
            'labels': [d['date'].strftime('%Y-%m-%d') for d in data],
            'data': [d['count'] for d in data],
            'label': 'Requests'
        })
    
    elif chart_type == 'categories':
        # Requests by category
        data = SupplyRequest.objects.filter(
            requested_at__gte=start_date
        ).values('supply__category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return JsonResponse({
            'labels': [d['supply__category__name'] for d in data],
            'data': [d['count'] for d in data],
            'label': 'Requests by Category'
        })
    
    elif chart_type == 'status':
        # Current request status breakdown
        data = SupplyRequest.objects.values('status').annotate(
            count=Count('id')
        )
        
        status_labels = dict(SupplyRequest.Status.choices)
        return JsonResponse({
            'labels': [status_labels.get(d['status'], d['status']) for d in data],
            'data': [d['count'] for d in data],
            'label': 'Request Status'
        })
    
    elif chart_type == 'stock':
        # Stock levels
        in_stock = Supply.objects.filter(is_active=True, quantity__gt=models.F('min_stock_level')).count()
        low_stock = Supply.objects.filter(is_active=True, quantity__lte=models.F('min_stock_level'), quantity__gt=0).count()
        out_of_stock = Supply.objects.filter(is_active=True, quantity=0).count()
        
        return JsonResponse({
            'labels': ['In Stock', 'Low Stock', 'Out of Stock'],
            'data': [in_stock, low_stock, out_of_stock],
            'label': 'Stock Status',
            'colors': ['#22c55e', '#f59e0b', '#ef4444']
        })
    
    return JsonResponse({'error': 'Unknown chart type'}, status=400)


# =============================================================================
# Notification Views
# =============================================================================

@login_required
def notifications_list(request):
    """List all notifications for the current user."""
    from .models import Notification
    
    filter_type = request.GET.get('filter', 'all')
    
    notifications_qs = Notification.objects.filter(user=request.user)
    
    if filter_type == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)
    elif filter_type == 'read':
        notifications_qs = notifications_qs.filter(is_read=True)
    
    notifications_qs = notifications_qs.order_by('-created_at')
    
    paginator = Paginator(notifications_qs, 20)
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)
    
    # Count stats
    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'notifications_list': notifications_page,
        'current_filter': filter_type,
        'total_count': total_count,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/list.html', context)


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark a single notification as read."""
    from .models import Notification
    
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('HX-Request'):
        return HttpResponse('')  # Return empty for HTMX to remove the item
    
    # Redirect to the notification's link if available
    if notification.link:
        return redirect(notification.link)
    
    return redirect('notifications')


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark all notifications as read."""
    from .models import Notification
    
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    if request.headers.get('HX-Request'):
        return HttpResponse('<span class="text-surface-500 text-sm">All caught up!</span>')
    
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications')


@login_required
@require_POST
def notification_delete(request, pk):
    """Delete a notification."""
    from .models import Notification
    
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    
    if request.headers.get('HX-Request'):
        return HttpResponse('')
    
    messages.success(request, 'Notification deleted.')
    return redirect('notifications')


@login_required
@require_POST
def notification_delete_all_read(request):
    """Delete all read notifications."""
    from .models import Notification
    
    deleted_count = Notification.objects.filter(user=request.user, is_read=True).delete()[0]
    
    messages.success(request, f'Deleted {deleted_count} read notifications.')
    return redirect('notifications')


@login_required
@require_GET
def api_notifications(request):
    """API endpoint to get notifications (for AJAX polling)."""
    from .models import Notification
    
    notifications_qs = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    data = {
        'count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'created_at': n.created_at.isoformat(),
                'time_ago': f"{(timezone.now() - n.created_at).seconds // 60} min ago" if (timezone.now() - n.created_at).seconds < 3600 else n.created_at.strftime('%b %d, %H:%M'),
            }
            for n in notifications_qs
        ]
    }
    
    return JsonResponse(data)


@login_required
def notifications_dropdown(request):
    """HTMX partial for notification dropdown content."""
    from .models import Notification
    
    notifications_qs = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:8]
    
    return render(request, 'partials/notifications_dropdown.html', {
        'dropdown_notifications': notifications_qs,
    })


# =============================================================================
# Batch Request Creation
# =============================================================================

@login_required
def batch_request_create(request):
    """Create a batch request with multiple items."""
    from .models import Notification
    
    if request.user.has_overdue_items:
        messages.error(request, 'You have overdue items. Please return them before making new requests.')
        return redirect('my_requests')
    
    if request.method == 'POST':
        # Get form data
        purpose = request.POST.get('purpose', '')
        priority = request.POST.get('priority', 'normal')
        needed_by = request.POST.get('needed_by')
        
        # Get selected items (format: supply_id:quantity or instance_id for equipment)
        selected_items = request.POST.getlist('selected_items')
        
        if not selected_items:
            messages.error(request, 'Please select at least one item.')
            return redirect('batch_request_create')
        
        # Generate batch group ID
        batch_id = uuid.uuid4()
        created_requests = []
        
        for item in selected_items:
            parts = item.split(':')
            
            if parts[0] == 'supply':
                # Consumable supply request
                supply_id = int(parts[1])
                quantity = int(parts[2]) if len(parts) > 2 else 1
                
                supply = Supply.objects.get(pk=supply_id, is_active=True)
                
                supply_request = SupplyRequest.objects.create(
                    requester=request.user,
                    supply=supply,
                    quantity=quantity,
                    purpose=purpose,
                    priority=priority,
                    needed_by=needed_by if needed_by else None,
                    batch_group_id=batch_id,
                )
                created_requests.append(supply_request)
                
            elif parts[0] == 'instance':
                # Equipment instance request
                instance_id = int(parts[1])
                instance = EquipmentInstance.objects.get(pk=instance_id, is_active=True)
                
                supply_request = SupplyRequest.objects.create(
                    requester=request.user,
                    supply=instance.supply,
                    quantity=1,
                    purpose=purpose,
                    priority=priority,
                    needed_by=needed_by if needed_by else None,
                    requested_instance=instance,
                    batch_group_id=batch_id,
                )
                created_requests.append(supply_request)
        
        # Update user analytics
        analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=request.user)
        analytics.total_requests += len(created_requests)
        analytics.last_request_at = timezone.now()
        analytics.save()
        
        # Notify GSO staff about new batch request
        if created_requests:
            Notification.notify_new_request_to_gso(created_requests[0])
        
        messages.success(request, f'Batch request created with {len(created_requests)} items! Reference: {created_requests[0].request_code}')
        return redirect('my_requests')
    
    # GET request - show form
    # Get available supplies (consumables)
    # Show all active consumables regardless of quantity (user can still request)
    consumable_supplies = Supply.objects.filter(
        is_active=True,
        is_consumable=True
    ).select_related('category').order_by('category', 'name')
    
    # Get available equipment instances
    equipment_instances = EquipmentInstance.objects.filter(
        is_active=True,
        status=EquipmentInstance.Status.AVAILABLE
    ).select_related('supply', 'supply__category').order_by('supply__category', 'supply__name', 'instance_code')
    
    categories = SupplyCategory.objects.filter(is_active=True)
    
    context = {
        'consumable_supplies': consumable_supplies,
        'equipment_instances': equipment_instances,
        'categories': categories,
        'priority_choices': SupplyRequest.Priority.choices,
    }
    
    return render(request, 'requests/batch_create.html', context)


@login_required
def batch_request_detail(request, batch_id):
    """View details of a batch request."""
    batch_requests = SupplyRequest.objects.filter(
        batch_group_id=batch_id
    ).select_related('supply', 'requester', 'reviewed_by', 'requested_instance')
    
    if not batch_requests.exists():
        messages.error(request, 'Batch request not found.')
        return redirect('my_requests')
    
    first_request = batch_requests.first()
    
    # Check access
    if first_request.requester != request.user and request.user.role == User.Role.DEPARTMENT_USER:
        messages.error(request, 'You do not have permission to view this request.')
        return redirect('my_requests')
    
    # Get all borrowed items for this batch
    borrowed_items = BorrowedItem.objects.filter(
        request__batch_group_id=batch_id
    ).select_related('equipment_instance', 'borrower')
    
    # Calculate returned count for progress tracking
    returned_count = borrowed_items.filter(returned_at__isnull=False).count()
    
    context = {
        'batch_id': batch_id,
        'batch_requests': batch_requests,
        'first_request': first_request,
        'borrowed_items': borrowed_items,
        'total_items': batch_requests.count(),
        'returned_count': returned_count,
    }
    
    return render(request, 'requests/batch_detail.html', context)


@login_required
@require_POST
def batch_approve(request, batch_id):
    """Approve all requests in a batch."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    batch_requests = SupplyRequest.objects.filter(
        batch_group_id=batch_id,
        status=SupplyRequest.Status.PENDING
    )
    
    if not batch_requests.exists():
        messages.error(request, 'No pending requests found in this batch.')
        return redirect('pending_requests')
    
    notes = request.POST.get('notes', '')
    approved_count = 0
    
    for supply_request in batch_requests:
        supply_request.approve(request.user, notes)
        approved_count += 1
        
        # Update requester analytics
        analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=supply_request.requester)
        analytics.approved_requests += 1
        analytics.save()
    
    # Send notification to requester
    first_request = batch_requests.first()
    if first_request:
        Notification.notify_request_approved(first_request)
    
    messages.success(request, f'Approved {approved_count} items in batch.')
    return redirect('pending_requests')

@login_required
@require_POST
def batch_reject(request, batch_id):
    """Reject all requests in a batch."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    batch_requests = SupplyRequest.objects.filter(
        batch_group_id=batch_id,
        status=SupplyRequest.Status.PENDING
    )
    
    if not batch_requests.exists():
        messages.error(request, 'No pending requests found in this batch.')
        return redirect('pending_requests')
    
    notes = request.POST.get('notes', 'Batch rejected')
    rejected_count = 0
    
    for supply_request in batch_requests:
        supply_request.reject(request.user, notes)
        rejected_count += 1
        
    messages.success(request, f'Rejected {rejected_count} items in batch.')
    return redirect('pending_requests')


@login_required
@require_POST
def batch_issue(request, batch_id):
    """Issue all approved items in a batch."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    batch_requests = SupplyRequest.objects.filter(
        batch_group_id=batch_id,
        status=SupplyRequest.Status.APPROVED
    ).select_related('supply', 'requester', 'requested_instance')
    
    if not batch_requests.exists():
        messages.error(request, 'No approved requests found in this batch.')
        return redirect('pending_requests')
    
    issued_count = 0
    errors = []
    
    for supply_request in batch_requests:
        try:
            if supply_request.supply.is_consumable:
                # Handle consumables
                supply = supply_request.supply
                if supply.quantity < supply_request.quantity:
                    errors.append(f'Insufficent quantity for {supply.name}')
                    continue
                
                previous_qty = supply.quantity
                supply.quantity -= supply_request.quantity
                supply.save()
                
                # Update request status
                supply_request.status = SupplyRequest.Status.ISSUED
                supply_request.issued_by = request.user
                supply_request.issued_at = timezone.now()
                supply_request.save()
                
                # Log transaction
                InventoryTransaction.objects.create(
                    supply=supply,
                    transaction_type=InventoryTransaction.TransactionType.OUT,
                    quantity=-supply_request.quantity,
                    previous_quantity=previous_qty,
                    new_quantity=supply.quantity,
                    reference_code=supply_request.request_code,
                    supply_request=supply_request,
                    performed_by=request.user,
                )
                
                issued_count += 1
                continue

            # Handle equipment (as before)
            if supply_request.requested_instance:
                instance = supply_request.requested_instance
                if instance.status != EquipmentInstance.Status.AVAILABLE:
                    errors.append(f'{instance.instance_code} is not available')
                    continue
            else:
                # Find an available instance
                instance = supply_request.supply.instances.filter(
                    is_active=True,
                    status=EquipmentInstance.Status.AVAILABLE
                ).first()
                
                if not instance:
                    errors.append(f'No available instance for {supply_request.supply.name}')
                    continue
            
            # Create borrowed item
            borrowed_item = BorrowedItem.objects.create(
                request=supply_request,
                equipment_instance=instance,
                borrower=supply_request.requester,
                return_deadline=timezone.now() + timedelta(days=supply_request.supply.default_borrow_days)
            )
            
            # Update instance status
            instance.status = EquipmentInstance.Status.BORROWED
            instance.last_borrowed_by = supply_request.requester
            instance.last_borrowed_at = timezone.now()
            instance.save()
            
            # Update request status
            supply_request.status = SupplyRequest.Status.ISSUED
            supply_request.issued_by = request.user
            supply_request.issued_at = timezone.now()
            supply_request.save()
            
            # Log transaction
            InventoryTransaction.objects.create(
                supply=supply_request.supply,
                equipment_instance=instance,
                transaction_type=InventoryTransaction.TransactionType.OUT,
                quantity=-1,
                previous_quantity=supply_request.supply.quantity,
                new_quantity=supply_request.supply.quantity,
                reference_code=supply_request.request_code,
                supply_request=supply_request,
                borrowed_item=borrowed_item,
                performed_by=request.user,
            )
            
            # Update borrower analytics
            analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=supply_request.requester)
            analytics.update_from_borrow(borrowed_item)
            
            # Send notification
            Notification.notify_item_issued(borrowed_item)
            
            issued_count += 1
            
        except Exception as e:
            errors.append(f'Error issuing {supply_request.supply.name}: {str(e)}')
    
    if issued_count > 0:
        messages.success(request, f'Issued {issued_count} items successfully.')
    if errors:
        for error in errors[:3]:
            messages.warning(request, error)
    
    if request.headers.get('HX-Request') or request.headers.get('X-Up-Target'):
        response = HttpResponse('')
        target_url = reverse('batch_request_detail', args=[batch_id])
        response['HX-Redirect'] = target_url
        response['X-Up-Location'] = target_url
        return response

    return redirect('returns')

@login_required
@require_POST
def batch_return(request, batch_id):
    """Return all borrowed items in a batch."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    borrowed_items = BorrowedItem.objects.filter(
        request__batch_group_id=batch_id,
        returned_at__isnull=True
    ).select_related('equipment_instance', 'equipment_instance__supply')
    
    if not borrowed_items.exists():
        messages.info(request, 'All items in this batch have already been returned.')
        return redirect('returns')
        
    status = request.POST.get('status', BorrowedItem.ReturnStatus.GOOD)
    notes = request.POST.get('notes', 'Batch return via detail page')
    
    returned_count = 0
    for item in borrowed_items:
        item.process_return(request.user, status, notes)
        returned_count += 1
        
    messages.success(request, f'Successfully processed return for {returned_count} batch items.')
    return redirect('returns')


# =============================================================================
# Return Scanner with Condition Selection
# =============================================================================

@login_required
def return_scanner(request):
    """QR scanner interface specifically for returns with condition selection."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    # Get currently borrowed items for reference
    borrowed_items = BorrowedItem.objects.filter(
        returned_at__isnull=True
    ).select_related(
        'equipment_instance', 'equipment_instance__supply', 'borrower', 'request'
    ).order_by('return_deadline')[:20]
    
    context = {
        'borrowed_items': borrowed_items,
        'return_status_choices': BorrowedItem.ReturnStatus.choices,
    }
    
    return render(request, 'scanner/return_scanner.html', context)


@login_required
@require_POST
def process_return_scan(request):
    """Process a QR scan for return and show condition selection."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    qr_data = request.POST.get('qr_data', '')
    
    result = {'success': False, 'message': 'Unknown QR code format'}
    
    try:
        if qr_data.startswith('INSTANCE-'):
            # Equipment instance scan
            instance_id = qr_data.split('-')[1]
            instance = EquipmentInstance.objects.get(id=instance_id)
            
            # Find the active borrowed item for this instance
            borrowed_item = BorrowedItem.objects.filter(
                equipment_instance=instance,
                returned_at__isnull=True
            ).select_related('borrower', 'request', 'request__supply').first()
            
            if borrowed_item:
                result = {
                    'success': True,
                    'type': 'borrowed_item',
                    'data': {
                        'borrowed_item_id': borrowed_item.id,
                        'instance_code': instance.instance_code,
                        'supply_name': instance.supply.name,
                        'borrower_name': borrowed_item.borrower.get_full_name(),
                        'borrower_department': borrowed_item.borrower.department.name if borrowed_item.borrower.department else 'N/A',
                        'borrowed_at': borrowed_item.borrowed_at.strftime('%Y-%m-%d %H:%M'),
                        'return_deadline': borrowed_item.return_deadline.strftime('%Y-%m-%d %H:%M'),
                        'is_overdue': borrowed_item.is_overdue,
                        'overdue_days': borrowed_item.overdue_days,
                        'batch_id': str(borrowed_item.request.batch_group_id) if borrowed_item.request.batch_group_id else None,
                    }
                }
            else:
                result = {
                    'success': False,
                    'message': f'Item {instance.instance_code} is not currently borrowed.',
                    'data': {
                        'instance_code': instance.instance_code,
                        'status': instance.get_status_display(),
                    }
                }
        elif qr_data.startswith('BORROW-') and not qr_data.startswith('BORROW-BATCH-'):
            # Individual request scan
            request_id = qr_data.replace('BORROW-', '').split('-')[0]
            supply_request = SupplyRequest.objects.get(id=request_id)
            
            # Find the active borrowed item for this request
            borrowed_item = BorrowedItem.objects.filter(
                request=supply_request,
                returned_at__isnull=True
            ).select_related('borrower', 'request', 'request__supply', 'equipment_instance').first()
            
            if borrowed_item:
                instance = borrowed_item.equipment_instance
                result = {
                    'success': True,
                    'type': 'borrowed_item',
                    'data': {
                        'borrowed_item_id': borrowed_item.id,
                        'instance_code': instance.instance_code,
                        'supply_name': instance.supply.name,
                        'borrower_name': borrowed_item.borrower.get_full_name(),
                        'borrower_department': borrowed_item.borrower.department.name if borrowed_item.borrower.department else 'N/A',
                        'borrowed_at': borrowed_item.borrowed_at.strftime('%Y-%m-%d %H:%M'),
                        'return_deadline': borrowed_item.return_deadline.strftime('%Y-%m-%d %H:%M'),
                        'is_overdue': borrowed_item.is_overdue,
                        'overdue_days': borrowed_item.overdue_days,
                        'batch_id': str(borrowed_item.request.batch_group_id) if borrowed_item.request.batch_group_id else None,
                    }
                }
            else:
                result = {'success': False, 'message': 'No active borrowing found for this request.'}
        else:
            result = {
                'success': False,
                'message': 'Please scan an equipment instance QR code.'
            }
            
    except EquipmentInstance.DoesNotExist:
        result = {'success': False, 'message': 'Equipment instance not found.'}
    except Exception as e:
        result = {'success': False, 'message': str(e)}
    
    return JsonResponse(result)


@login_required
@require_POST
def confirm_return(request):
    """Confirm the return of an item with condition selection."""
    from .models import Notification
    
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    borrowed_item_id = request.POST.get('borrowed_item_id')
    return_status = request.POST.get('return_status', 'good')
    notes = request.POST.get('notes', '')
    
    borrowed_item = get_object_or_404(BorrowedItem, pk=borrowed_item_id, returned_at__isnull=True)
    
    # Process the return
    borrowed_item.process_return(request.user, return_status, notes)
    
    # Update analytics
    analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=borrowed_item.borrower)
    analytics.update_from_return(borrowed_item)
    
    # Log transaction
    InventoryTransaction.objects.create(
        supply=borrowed_item.equipment_instance.supply,
        equipment_instance=borrowed_item.equipment_instance,
        transaction_type=InventoryTransaction.TransactionType.RETURN,
        quantity=1,
        previous_quantity=borrowed_item.equipment_instance.supply.quantity,
        new_quantity=borrowed_item.equipment_instance.supply.quantity,
        reference_code=borrowed_item.request.request_code,
        supply_request=borrowed_item.request,
        borrowed_item=borrowed_item,
        notes=f'Returned: {return_status}. {notes}',
        performed_by=request.user,
    )
    
    # Log scan
    QRScanLog.objects.create(
        scanned_by=request.user,
        qr_data=borrowed_item.equipment_instance.qr_data,
        scan_type=QRScanLog.ScanType.RETURN,
        equipment_instance=borrowed_item.equipment_instance,
        supply_request=borrowed_item.request,
        was_successful=True,
        notes=notes,
    )
    
    # Handle damage/loss
    if return_status in ['damaged', 'lost']:
        StockAdjustment.objects.create(
            supply=borrowed_item.equipment_instance.supply,
            equipment_instance=borrowed_item.equipment_instance,
            reason=StockAdjustment.AdjustmentReason.DAMAGE if return_status == 'damaged' else StockAdjustment.AdjustmentReason.LOSS,
            quantity=-1,
            description=notes or f'Item {return_status} upon return',
            is_penalty=True,
            responsible_user=borrowed_item.borrower,
            borrowed_item=borrowed_item,
            adjusted_by=request.user,
        )
    
    # Check if this was part of a batch and all items are now returned
    batch_id = borrowed_item.request.batch_group_id
    batch_status = None
    
    if batch_id:
        remaining = BorrowedItem.objects.filter(
            request__batch_group_id=batch_id,
            returned_at__isnull=True
        ).count()
        
        batch_status = {
            'batch_id': str(batch_id),
            'remaining_items': remaining,
            'all_returned': remaining == 0
        }
    
    return JsonResponse({
        'success': True,
        'message': f'Return processed for {borrowed_item.equipment_instance.instance_code}',
        'return_status': return_status,
        'batch_status': batch_status,
    })


@login_required
def batch_return_status(request, batch_id):
    """Get the return status of all items in a batch."""
    if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    borrowed_items = BorrowedItem.objects.filter(
        request__batch_group_id=batch_id
    ).select_related('equipment_instance', 'borrower')
    
    items = []
    for item in borrowed_items:
        items.append({
            'id': item.id,
            'instance_code': item.equipment_instance.instance_code,
            'supply_name': item.equipment_instance.supply.name,
            'borrower': item.borrower.get_full_name(),
            'borrowed_at': item.borrowed_at.strftime('%Y-%m-%d %H:%M'),
            'return_deadline': item.return_deadline.strftime('%Y-%m-%d %H:%M'),
            'returned_at': item.returned_at.strftime('%Y-%m-%d %H:%M') if item.returned_at else None,
            'return_status': item.return_status,
            'is_overdue': item.is_overdue,
        })
    
    total = len(items)
    returned = sum(1 for i in items if i['returned_at'])
    
    return JsonResponse({
        'batch_id': str(batch_id),
        'total_items': total,
        'returned_items': returned,
        'pending_items': total - returned,
        'all_returned': returned == total,
        'items': items,
    })
