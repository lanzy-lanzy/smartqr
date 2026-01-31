"""
Context processors for Smart Supply.

These functions add variables to the template context for all templates.
"""

from .models import Notification


def notifications(request):
    """
    Add notification data to all templates.
    
    Provides:
        - notifications: QuerySet of user's unread notifications (limited to 10)
        - notifications_count: Total count of unread notifications
        - notifications_unread_count: Same as above (for clarity)
    """
    if not request.user.is_authenticated:
        return {
            'notifications': [],
            'notifications_count': 0,
            'notifications_unread_count': 0,
        }
    
    # Get unread notifications for the current user
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).select_related('related_request', 'related_borrowed_item')[:10]
    
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return {
        'notifications': unread_notifications,
        'notifications_count': unread_count,
        'notifications_unread_count': unread_count,
    }


def user_permissions(request):
    """
    Add user permission helpers to all templates.
    
    Provides:
        - is_gso_or_admin: Boolean if user is GSO staff or admin
        - can_approve_requests: Boolean if user can approve requests
        - can_manage_users: Boolean if user is admin
    """
    if not request.user.is_authenticated:
        return {
            'is_gso_or_admin': False,
            'can_approve_requests': False,
            'can_manage_users': False,
        }
    
    from .models import User
    
    is_gso_or_admin = request.user.role in [User.Role.GSO_STAFF, User.Role.ADMIN]
    
    return {
        'is_gso_or_admin': is_gso_or_admin,
        'can_approve_requests': is_gso_or_admin,
        'can_manage_users': request.user.role == User.Role.ADMIN,
    }
