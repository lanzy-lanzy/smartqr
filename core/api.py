"""
REST API Module for Smart Supply

Provides JSON API endpoints for external integrations.
Uses Django's built-in JsonResponse for simplicity.
For full REST API capabilities, consider using Django REST Framework.
"""
import json
from functools import wraps
from datetime import datetime, timedelta
from django.conf import settings
import google.generativeai as genai

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator

from .models import (
    User, Department, SupplyCategory, Supply, EquipmentInstance,
    SupplyRequest, BorrowedItem, AuditLog
)


# =============================================================================
# Authentication Decorator
# =============================================================================

def api_login_required(view_func):
    """
    Decorator for API authentication.
    Supports both session auth and token auth (Basic Auth style).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check session auth first
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Basic '):
            import base64
            try:
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                email, password = credentials.split(':', 1)
                user = authenticate(request, username=email, password=password)
                if user and user.is_approved:
                    request.user = user
                    return view_func(request, *args, **kwargs)
            except:
                pass
        
        return JsonResponse({
            'error': 'Authentication required',
            'code': 'auth_required'
        }, status=401)
    
    return wrapper


def api_staff_required(view_func):
    """Decorator requiring GSO Staff or Admin role."""
    @wraps(view_func)
    @api_login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role not in [User.Role.ADMIN, User.Role.GSO_STAFF]:
            return JsonResponse({
                'error': 'Staff access required',
                'code': 'permission_denied'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def api_admin_required(view_func):
    """Decorator requiring Admin role."""
    @wraps(view_func)
    @api_login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            return JsonResponse({
                'error': 'Admin access required',
                'code': 'permission_denied'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# Serialization Helpers
# =============================================================================

def serialize_user(user, detail=False):
    """Serialize User object."""
    data = {
        'id': user.id,
        'email': user.email,
        'full_name': user.get_full_name(),
        'role': user.role,
        'department': user.department.name if user.department else None,
    }
    if detail:
        data.update({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'approval_status': user.approval_status,
            'is_active': user.is_active,
            'has_overdue_items': user.has_overdue_items,
            'created_at': user.created_at.isoformat(),
        })
    return data


def serialize_supply(supply, detail=False):
    """Serialize Supply object."""
    data = {
        'id': supply.id,
        'name': supply.name,
        'category': supply.category.name,
        'category_id': supply.category_id,
        'quantity': supply.quantity,
        'available_quantity': supply.available_quantity,
        'unit': supply.unit,
        'stock_status': supply.stock_status,
        'is_consumable': supply.is_consumable,
    }
    if detail:
        data.update({
            'description': supply.description,
            'min_stock_level': supply.min_stock_level,
            'default_borrow_days': supply.default_borrow_days,
            'is_active': supply.is_active,
            'qr_data': supply.qr_data,
            'created_at': supply.created_at.isoformat(),
        })
    return data


def serialize_instance(instance, detail=False):
    """Serialize EquipmentInstance object."""
    data = {
        'id': instance.id,
        'instance_code': instance.instance_code,
        'supply_id': instance.supply_id,
        'supply_name': instance.supply.name,
        'status': instance.status,
        'is_available': instance.is_available,
    }
    if detail:
        data.update({
            'serial_number': instance.serial_number,
            'condition_notes': instance.condition_notes,
            'qr_data': instance.qr_data,
            'acquired_date': instance.acquired_date.isoformat() if instance.acquired_date else None,
            'warranty_expiry': instance.warranty_expiry.isoformat() if instance.warranty_expiry else None,
            'current_borrower': serialize_user(instance.current_borrower) if instance.current_borrower else None,
        })
    return data


def serialize_request(supply_request, detail=False):
    """Serialize SupplyRequest object."""
    data = {
        'id': supply_request.id,
        'request_code': supply_request.request_code,
        'supply_id': supply_request.supply_id,
        'supply_name': supply_request.supply.name,
        'quantity': supply_request.quantity,
        'status': supply_request.status,
        'priority': supply_request.priority,
        'requester': serialize_user(supply_request.requester),
        'requested_at': supply_request.requested_at.isoformat(),
    }
    if detail:
        data.update({
            'purpose': supply_request.purpose,
            'needed_by': supply_request.needed_by.isoformat() if supply_request.needed_by else None,
            'reviewed_by': serialize_user(supply_request.reviewed_by) if supply_request.reviewed_by else None,
            'reviewed_at': supply_request.reviewed_at.isoformat() if supply_request.reviewed_at else None,
            'review_notes': supply_request.review_notes,
            'issued_at': supply_request.issued_at.isoformat() if supply_request.issued_at else None,
            'is_batch_request': supply_request.is_batch_request,
            'qr_data': supply_request.qr_data,
        })
    return data


def serialize_borrowed_item(item, detail=False):
    """Serialize BorrowedItem object."""
    data = {
        'id': item.id,
        'request_id': item.request_id,
        'request_code': item.request.request_code,
        'equipment_instance': serialize_instance(item.equipment_instance),
        'borrower': serialize_user(item.borrower),
        'borrowed_at': item.borrowed_at.isoformat(),
        'return_deadline': item.return_deadline.isoformat(),
        'is_overdue': item.is_overdue,
        'days_until_due': item.days_until_due,
    }
    if detail:
        data.update({
            'returned_at': item.returned_at.isoformat() if item.returned_at else None,
            'return_status': item.return_status,
            'return_notes': item.return_notes,
            'overdue_days': item.overdue_days,
        })
    return data


# =============================================================================
# API Endpoints - Supplies
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@api_login_required
def api_supplies_list(request):
    """
    GET /api/v1/supplies/
    
    Query params:
        - search: Search by name
        - category: Filter by category ID
        - status: Filter by stock status (in_stock, low_stock, out_of_stock)
        - page: Page number (default 1)
        - limit: Items per page (default 20, max 100)
    """
    supplies = Supply.objects.filter(is_active=True).select_related('category')
    
    # Filters
    search = request.GET.get('search', '')
    if search:
        supplies = supplies.filter(Q(name__icontains=search) | Q(description__icontains=search))
    
    category = request.GET.get('category')
    if category:
        supplies = supplies.filter(category_id=category)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    
    paginator = Paginator(supplies, limit)
    page_obj = paginator.get_page(page)
    
    return JsonResponse({
        'data': [serialize_supply(s) for s in page_obj],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': paginator.count,
            'pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@csrf_exempt
@require_http_methods(["GET"])
@api_login_required
def api_supply_detail(request, pk):
    """GET /api/v1/supplies/<id>/"""
    try:
        supply = Supply.objects.select_related('category').get(pk=pk, is_active=True)
    except Supply.DoesNotExist:
        return JsonResponse({'error': 'Supply not found'}, status=404)
    
    data = serialize_supply(supply, detail=True)
    
    # Include instances for equipment
    if not supply.is_consumable:
        data['instances'] = [
            serialize_instance(i) 
            for i in supply.instances.filter(is_active=True)
        ]
    
    return JsonResponse({'data': data})


# =============================================================================
# API Endpoints - Equipment Instances
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@api_login_required
def api_instances_list(request):
    """
    GET /api/v1/instances/
    
    Query params:
        - supply: Filter by supply ID
        - status: Filter by status
        - search: Search by code or serial
    """
    instances = EquipmentInstance.objects.filter(is_active=True).select_related('supply')
    
    supply_id = request.GET.get('supply')
    if supply_id:
        instances = instances.filter(supply_id=supply_id)
    
    status = request.GET.get('status')
    if status:
        instances = instances.filter(status=status)
    
    search = request.GET.get('search', '')
    if search:
        instances = instances.filter(
            Q(instance_code__icontains=search) | Q(serial_number__icontains=search)
        )
    
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    
    paginator = Paginator(instances, limit)
    page_obj = paginator.get_page(page)
    
    return JsonResponse({
        'data': [serialize_instance(i) for i in page_obj],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': paginator.count,
            'pages': paginator.num_pages,
        }
    })


# =============================================================================
# API Endpoints - Requests
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_login_required
def api_requests_list(request):
    """
    GET /api/v1/requests/ - List requests
    POST /api/v1/requests/ - Create new request
    """
    if request.method == 'GET':
        # Filter based on role
        if request.user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
            requests_qs = SupplyRequest.objects.all()
        else:
            requests_qs = SupplyRequest.objects.filter(requester=request.user)
        
        requests_qs = requests_qs.select_related('supply', 'requester')
        
        status = request.GET.get('status')
        if status:
            requests_qs = requests_qs.filter(status=status)
        
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        paginator = Paginator(requests_qs, limit)
        page_obj = paginator.get_page(page)
        
        return JsonResponse({
            'data': [serialize_request(r) for r in page_obj],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginator.count,
                'pages': paginator.num_pages,
            }
        })
    
    elif request.method == 'POST':
        # Check if user can make requests
        if request.user.has_overdue_items:
            return JsonResponse({
                'error': 'Cannot create request: you have overdue items',
                'code': 'overdue_block'
            }, status=400)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Validate required fields
        required = ['supply_id', 'quantity', 'purpose']
        for field in required:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        try:
            supply = Supply.objects.get(pk=data['supply_id'], is_active=True)
        except Supply.DoesNotExist:
            return JsonResponse({'error': 'Supply not found'}, status=404)
        
        supply_request = SupplyRequest.objects.create(
            requester=request.user,
            supply=supply,
            quantity=data['quantity'],
            purpose=data['purpose'],
            priority=data.get('priority', 'normal'),
            needed_by=data.get('needed_by'),
        )
        
        # Log audit
        AuditLog.log(
            user=request.user,
            action=AuditLog.ActionType.CREATE,
            entity_type=AuditLog.EntityType.REQUEST,
            description=f"Created request {supply_request.request_code} via API",
            entity_id=supply_request.id,
            entity_repr=str(supply_request),
            request=request
        )
        
        return JsonResponse({
            'data': serialize_request(supply_request, detail=True),
            'message': 'Request created successfully'
        }, status=201)


@csrf_exempt
@require_http_methods(["GET"])
@api_login_required
def api_request_detail(request, pk):
    """GET /api/v1/requests/<id>/"""
    try:
        supply_request = SupplyRequest.objects.select_related('supply', 'requester').get(pk=pk)
    except SupplyRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)
    
    # Check access
    if supply_request.requester != request.user and request.user.role == User.Role.DEPARTMENT_USER:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    data = serialize_request(supply_request, detail=True)
    data['borrowed_items'] = [
        serialize_borrowed_item(bi) 
        for bi in supply_request.borrowed_items.all()
    ]
    
    return JsonResponse({'data': data})


@csrf_exempt
@require_http_methods(["POST"])
@api_staff_required
def api_request_approve(request, pk):
    """POST /api/v1/requests/<id>/approve/"""
    try:
        supply_request = SupplyRequest.objects.get(pk=pk, status=SupplyRequest.Status.PENDING)
    except SupplyRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found or not pending'}, status=404)
    
    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    
    notes = data.get('notes', '')
    supply_request.approve(request.user, notes)
    
    AuditLog.log(
        user=request.user,
        action=AuditLog.ActionType.APPROVE,
        entity_type=AuditLog.EntityType.REQUEST,
        description=f"Approved request {supply_request.request_code} via API",
        entity_id=supply_request.id,
        entity_repr=str(supply_request),
        request=request
    )
    
    return JsonResponse({
        'data': serialize_request(supply_request, detail=True),
        'message': 'Request approved'
    })


@csrf_exempt
@require_http_methods(["POST"])
@api_staff_required
def api_request_reject(request, pk):
    """POST /api/v1/requests/<id>/reject/"""
    try:
        supply_request = SupplyRequest.objects.get(pk=pk, status=SupplyRequest.Status.PENDING)
    except SupplyRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found or not pending'}, status=404)
    
    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    
    notes = data.get('notes', 'Rejected via API')
    supply_request.reject(request.user, notes)
    
    AuditLog.log(
        user=request.user,
        action=AuditLog.ActionType.REJECT,
        entity_type=AuditLog.EntityType.REQUEST,
        description=f"Rejected request {supply_request.request_code} via API",
        entity_id=supply_request.id,
        entity_repr=str(supply_request),
        request=request
    )
    
    return JsonResponse({
        'data': serialize_request(supply_request, detail=True),
        'message': 'Request rejected'
    })


# =============================================================================
# API Endpoints - Borrowed Items
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@api_login_required
def api_borrowed_list(request):
    """GET /api/v1/borrowed/"""
    if request.user.role in [User.Role.ADMIN, User.Role.GSO_STAFF]:
        items = BorrowedItem.objects.all()
    else:
        items = BorrowedItem.objects.filter(borrower=request.user)
    
    items = items.select_related('equipment_instance', 'borrower', 'request')
    
    active_only = request.GET.get('active', 'false').lower() == 'true'
    if active_only:
        items = items.filter(returned_at__isnull=True)
    
    overdue_only = request.GET.get('overdue', 'false').lower() == 'true'
    if overdue_only:
        items = items.filter(returned_at__isnull=True, return_deadline__lt=timezone.now())
    
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 20)), 100)
    
    paginator = Paginator(items, limit)
    page_obj = paginator.get_page(page)
    
    return JsonResponse({
        'data': [serialize_borrowed_item(bi, detail=True) for bi in page_obj],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': paginator.count,
            'pages': paginator.num_pages,
        }
    })


# =============================================================================
# API Endpoints - Statistics
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@api_staff_required
def api_stats(request):
    """GET /api/v1/stats/ - Get system statistics"""
    now = timezone.now()
    
    stats = {
        'supplies': {
            'total': Supply.objects.filter(is_active=True).count(),
            'low_stock': Supply.objects.filter(
                is_active=True, 
                quantity__lte=models.F('min_stock_level'),
                quantity__gt=0
            ).count(),
            'out_of_stock': Supply.objects.filter(is_active=True, quantity=0).count(),
        },
        'instances': {
            'total': EquipmentInstance.objects.filter(is_active=True).count(),
            'available': EquipmentInstance.objects.filter(
                is_active=True, 
                status=EquipmentInstance.Status.AVAILABLE
            ).count(),
            'borrowed': EquipmentInstance.objects.filter(
                is_active=True, 
                status=EquipmentInstance.Status.BORROWED
            ).count(),
        },
        'requests': {
            'total': SupplyRequest.objects.count(),
            'pending': SupplyRequest.objects.filter(status=SupplyRequest.Status.PENDING).count(),
            'approved': SupplyRequest.objects.filter(status=SupplyRequest.Status.APPROVED).count(),
        },
        'borrowed_items': {
            'active': BorrowedItem.objects.filter(returned_at__isnull=True).count(),
            'overdue': BorrowedItem.objects.filter(
                returned_at__isnull=True,
                return_deadline__lt=now
            ).count(),
        },
        'users': {
            'total': User.objects.count(),
            'active': User.objects.filter(approval_status=User.ApprovalStatus.APPROVED).count(),
            'pending': User.objects.filter(approval_status=User.ApprovalStatus.PENDING).count(),
        },
    }
    
    return JsonResponse({'data': stats})


# =============================================================================
# AI Assistant Endpoints
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@api_staff_required
def api_ai_suggest_supply(request):
    """
    GET /api/v1/ai/suggest-supply/?name=...
    
    Uses Gemini AI to suggest details for a supply based on its name.
    """
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Name parameter is required'}, status=400)
    
    if not settings.GOOGLE_API_KEY:
        return JsonResponse({'error': 'Gemini API key not configured'}, status=503)
    
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Get existing categories to help the AI map to one
        categories = list(SupplyCategory.objects.filter(is_active=True).values('id', 'name', 'is_material'))
        categories_str = ", ".join([f"{c['name']} (ID: {c['id']}, {'Equipment' if c['is_material'] else 'Consumable'})" for c in categories])
        
        prompt = f"""
        Suggest details for an inventory item named "{name}".
        Available categories: {categories_str}
        
        Return the result ONLY as a JSON object with these fields:
        - corrected_name: A standardized, professional name for the item (e.g., "thinkpad l14" -> "Lenovo ThinkPad L14").
        - description: A concise professional description (1-2 sentences).
        - category_id: Choose the most appropriate ID from the provided categories.
        - unit: The standard unit of measurement (e.g., piece, box, set, unit).
        - min_stock_level: Suggested minimum stock level (an integer).
        - is_consumable: Boolean (true if it's used up like paper/ink, false if it's durable like a laptop).
        
        Example:
        {{"corrected_name": "HP LaserJet Pro M404n", "description": "High-performance monochrome laser printer for office use.", "category_id": 2, "unit": "unit", "min_stock_level": 2, "is_consumable": false}}
        """
        
        response = model.generate_content(prompt)
        # Clean response text in case it includes markdown code blocks
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        return JsonResponse({'data': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@api_staff_required
def api_ai_suggest_prefix(request):
    """
    GET /api/v1/ai/suggest-prefix/?name=...
    
    Uses Gemini AI to suggest a professional instance code prefix based on supply name.
    """
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Name parameter is required'}, status=400)
    
    if not settings.GOOGLE_API_KEY:
        return JsonResponse({'error': 'Gemini API key not configured'}, status=503)
    
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        prompt = f"""
        Suggest a professional 3-4 letter shorthand prefix for inventory tracking of "{name}".
        Example: "ThinkPad L14" -> "LPT" or "TPL"
        Return ONLY the prefix in uppercase.
        """
        
        response = model.generate_content(prompt)
        prefix = response.text.strip().upper()[:5]
        
        return JsonResponse({'data': {'prefix': prefix}})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@api_staff_required
def api_ai_suggest_serials(request):
    """
    GET /api/v1/ai/suggest-serials/?name=...&count=10
    
    Uses Gemini AI to suggest realistic test serial numbers for a given equipment name.
    """
    name = request.GET.get('name')
    count = request.GET.get('count', 10)
    
    if not name:
        return JsonResponse({'error': 'Name parameter is required'}, status=400)
    
    if not settings.GOOGLE_API_KEY:
        return JsonResponse({'error': 'Gemini API key not configured'}, status=503)
    
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        prompt = f"""
        Generate {count} realistic but fake test serial numbers for equipment named "{name}".
        Return ONLY the serial numbers, one per line.
        """
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        serials = [s.strip() for s in content.split('\n') if s.strip()]
        
        return JsonResponse({'data': {'serials': serials}})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@api_staff_required
def api_ai_suggest_category(request):
    """
    GET /api/v1/ai/suggest-category/?name=...
    
    Uses Gemini AI to suggest category details: icon, description, and type.
    """
    name = request.GET.get('name')
    if not name:
        return JsonResponse({'error': 'Name parameter is required'}, status=400)
    
    if not settings.GOOGLE_API_KEY:
        return JsonResponse({'error': 'Gemini API key not configured'}, status=503)
    
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        prompt = f"""
        Suggest details for an inventory category named "{name}".
        
        Return the result ONLY as a JSON object with these fields:
        - icon: A standard Lucide icon name that fits this category (e.g., monitor, printer, package, hard-drive, cpu, mouse, keyboard, briefcase, tool, coffee).
        - description: A concise professional description (1-2 sentences).
        - is_material: Boolean (true if it contains durable equipment to be borrowed/returned, false if it contains consumables).
        
        Example for "IT Equipment":
        {{"icon": "monitor", "description": "Laptops, desktops, monitors, and other computing hardware.", "is_material": true}}
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        return JsonResponse({'data': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Import models for F expression
from django.db import models
