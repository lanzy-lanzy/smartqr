import uuid
import io
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.files.base import ContentFile

try:
    import qrcode
    from PIL import Image
    HAS_QR_LIBS = True
except ImportError:
    HAS_QR_LIBS = False


# =============================================================================
# User & Role Management
# =============================================================================

class Department(models.Model):
    """Represents organizational departments that users belong to."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short code (e.g., IT, HR, FIN)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserManager(BaseUserManager):
    """Custom manager for User model with role-based creation."""
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if email:
            email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('approval_status', User.ApprovalStatus.APPROVED)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with roles and approval states.
    
    Roles:
        - Admin: Full system access
        - GSO Staff: Manages inventory and processes requests
        - Department User: Can request items from their department
    
    Approval States:
        - Pending: Awaiting admin approval
        - Approved: Can use the system
        - Rejected: Access denied
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        GSO_STAFF = 'gso_staff', 'GSO Staff'
        DEPARTMENT_USER = 'department_user', 'Department User'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    # Use username as primary identifier (re-enable from AbstractUser)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField('email address', blank=True)
    
    # Role and status
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DEPARTMENT_USER
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING
    )
    
    # Profile fields
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} (@{self.username})"

    @property
    def is_approved(self):
        return self.approval_status == self.ApprovalStatus.APPROVED

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_gso_staff(self):
        return self.role == self.Role.GSO_STAFF

    @property
    def is_department_user(self):
        return self.role == self.Role.DEPARTMENT_USER

    @property
    def overdue_items(self):
        """Returns queryset of overdue borrowed items for this user."""
        return self.borrowed_items.filter(
            returned_at__isnull=True,
            return_deadline__lt=timezone.now()
        )

    @property
    def has_overdue_items(self):
        """Check if user has any overdue items (blocks new requests)."""
        return self.overdue_items.exists()

    @property
    def can_make_requests(self):
        """User can make requests if approved and no overdue items."""
        return self.is_approved and not self.has_overdue_items


# =============================================================================
# Supply & Inventory
# =============================================================================

class SupplyCategory(models.Model):
    """
    Category grouping for supplies.
    
    is_material: If True, items in this category are borrowable equipment
                 (e.g., laptops, projectors) that must be returned.
                 If False, items are consumables (e.g., paper, pens).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_material = models.BooleanField(
        default=False,
        help_text="If checked, items are borrowable equipment that must be returned"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class name (e.g., 'laptop', 'printer')"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Supply Categories'
        ordering = ['name']

    def __str__(self):
        category_type = "Equipment" if self.is_material else "Consumable"
        return f"{self.name} ({category_type})"


class Supply(models.Model):
    """
    Base template for an inventory item (e.g., "ThinkPad L14", "A4 Paper").
    
    For equipment (is_material=True categories), each physical unit is tracked
    via EquipmentInstance. For consumables, only stock quantity matters.
    """
    
    class StockStatus(models.TextChoices):
        IN_STOCK = 'in_stock', 'In Stock'
        LOW_STOCK = 'low_stock', 'Low Stock'
        OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        SupplyCategory,
        on_delete=models.PROTECT,
        related_name='supplies'
    )
    
    # Stock management
    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Current stock quantity (for consumables) or total units (for equipment)"
    )
    min_stock_level = models.PositiveIntegerField(
        default=5,
        help_text="Alert threshold for low stock"
    )
    
    # Borrowing settings (for equipment)
    is_consumable = models.BooleanField(
        default=True,
        help_text="If False, item must be returned after use"
    )
    default_borrow_days = models.PositiveIntegerField(
        default=3,
        help_text="Default number of days for borrowing"
    )
    
    # Metadata
    unit = models.CharField(
        max_length=20,
        default='pcs',
        help_text="Unit of measurement (pcs, box, ream, etc.)"
    )
    image = models.ImageField(
        upload_to='supply_images/',
        blank=True,
        null=True
    )
    qr_code = models.ImageField(
        upload_to='qr_codes/supplies/',
        blank=True,
        null=True
    )
    
    # Tracking
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_supplies'
    )

    class Meta:
        verbose_name_plural = 'Supplies'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def stock_status(self):
        """Calculate current stock status."""
        if self.quantity == 0:
            return self.StockStatus.OUT_OF_STOCK
        elif self.quantity <= self.min_stock_level:
            return self.StockStatus.LOW_STOCK
        return self.StockStatus.IN_STOCK

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_level

    @property
    def is_out_of_stock(self):
        return self.quantity == 0

    @property
    def available_quantity(self):
        """For equipment, count available instances. For consumables, use quantity."""
        if not self.is_consumable and self.category.is_material:
            return self.instances.filter(status=EquipmentInstance.Status.AVAILABLE).count()
        return self.quantity

    @property
    def qr_data(self):
        """QR encoding pattern for supplies."""
        clean_name = self.name.replace(' ', '-').upper()[:20]
        return f"SUPPLY-{self.id}-{clean_name}"

    def generate_qr_code(self):
        """Generate QR code image for this supply."""
        if not HAS_QR_LIBS:
            return None
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"supply_{self.id}_qr.png"
        self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
        return self.qr_code

    def save(self, *args, **kwargs):
        # Auto-set is_consumable based on category
        if self.category_id:
            self.is_consumable = not self.category.is_material
        
        # Save first to get the ID for QR data
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generate QR code if missing
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])


class EquipmentInstance(models.Model):
    """
    Represents a specific physical unit of equipment.
    
    Each instance has:
    - Unique serial number
    - Instance code (e.g., "LAPTOP-01")
    - Individual status tracking
    - Own QR code for scanning
    """
    
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        BORROWED = 'borrowed', 'Borrowed'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
        RETIRED = 'retired', 'Retired'
        LOST = 'lost', 'Lost'
        DAMAGED = 'damaged', 'Damaged'

    supply = models.ForeignKey(
        Supply,
        on_delete=models.CASCADE,
        related_name='instances'
    )
    
    # Identification
    instance_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier (e.g., LAPTOP-01, PROJ-03)"
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manufacturer serial number"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    condition_notes = models.TextField(
        blank=True,
        help_text="Notes about current condition"
    )
    
    # QR Code
    qr_code = models.ImageField(
        upload_to='qr_codes/instances/',
        blank=True,
        null=True
    )
    
    # Tracking
    last_borrowed_at = models.DateTimeField(null=True, blank=True)
    last_returned_at = models.DateTimeField(null=True, blank=True)
    last_borrowed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_borrowed_instances'
    )
    
    # Metadata
    acquired_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['supply', 'instance_code']
        verbose_name = 'Equipment Instance'
        verbose_name_plural = 'Equipment Instances'

    def save(self, *args, **kwargs):
        # Save first to get the ID for QR data
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generate QR code if missing
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def __str__(self):
        return f"{self.instance_code} ({self.supply.name}) - {self.get_status_display()}"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE

    @property
    def qr_data(self):
        """QR encoding pattern for instances."""
        return f"INSTANCE-{self.id}"

    def generate_qr_code(self):
        """Generate QR code image for this instance."""
        if not HAS_QR_LIBS:
            return None
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"instance_{self.id}_qr.png"
        self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
        return self.qr_code

    @property
    def current_borrower(self):
        """Get the current borrower if item is borrowed."""
        if self.status == self.Status.BORROWED:
            active_borrow = self.borrowed_items.filter(returned_at__isnull=True).first()
            if active_borrow:
                return active_borrow.request.requester
        return None


# =============================================================================
# Borrowing & Requests
# =============================================================================

class SupplyRequest(models.Model):
    """
    Represents a request to obtain supplies/equipment.
    
    Supports both individual requests and batch requests (multiple items
    in a single transaction, grouped by batch_group_id).
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ISSUED = 'issued', 'Issued'
        PARTIALLY_RETURNED = 'partially_returned', 'Partially Returned'
        RETURNED = 'returned', 'Returned'
        CANCELLED = 'cancelled', 'Cancelled'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    # Request identification
    request_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Auto-generated request code"
    )
    batch_group_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Groups multiple requests into a single batch"
    )
    
    # Requester info
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='supply_requests'
    )
    
    # What is being requested
    supply = models.ForeignKey(
        Supply,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    # Optional: specific instance requested
    requested_instance = models.ForeignKey(
        EquipmentInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_requests',
        help_text="Specific unit requested (optional)"
    )
    quantity = models.PositiveIntegerField(default=1)
    
    # Request details
    purpose = models.TextField(help_text="Reason for the request")
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Dates
    requested_at = models.DateTimeField(auto_now_add=True)
    needed_by = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the item is needed"
    )
    
    # Approval workflow
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Issuance
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_requests'
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    
    # QR Code for this request
    qr_code = models.ImageField(
        upload_to='qr_codes/requests/',
        blank=True,
        null=True
    )
    
    # Tracking
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.request_code} - {self.supply.name} by {self.requester}"

    def save(self, *args, **kwargs):
        if not self.request_code:
            # Generate request code: REQ-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_request = SupplyRequest.objects.filter(
                request_code__startswith=f'REQ-{today}'
            ).order_by('-request_code').first()
            
            if last_request:
                last_num = int(last_request.request_code.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.request_code = f"REQ-{today}-{new_num:04d}"
        
        super().save(*args, **kwargs)

    @property
    def qr_data(self):
        """QR encoding pattern for requests."""
        if self.batch_group_id:
            return f"BORROW-BATCH-{self.batch_group_id}"
        return f"BORROW-{self.id}-{self.requester_id}-{self.supply_id}"

    def generate_qr_code(self):
        """Generate QR code for this request."""
        if not HAS_QR_LIBS:
            return None
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"request_{self.id}_qr.png"
        self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
        return self.qr_code

    @property
    def is_batch_request(self):
        return self.batch_group_id is not None

    @property
    def batch_requests(self):
        """Get all requests in the same batch."""
        if self.batch_group_id:
            return SupplyRequest.objects.filter(batch_group_id=self.batch_group_id)
        return SupplyRequest.objects.filter(pk=self.pk)

    def approve(self, reviewed_by, notes=''):
        """Approve this request."""
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        self.generate_qr_code()
        self.save()

    def reject(self, reviewed_by, notes=''):
        """Reject this request."""
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class BorrowedItem(models.Model):
    """
    Tracks actual possession of non-consumable items.
    
    Created when a SupplyRequest for equipment is issued.
    Tracks borrow dates, return deadlines, and return condition.
    """
    
    class ReturnStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Return'
        GOOD = 'good', 'Returned in Good Condition'
        DAMAGED = 'damaged', 'Returned Damaged'
        LOST = 'lost', 'Lost'

    request = models.ForeignKey(
        SupplyRequest,
        on_delete=models.CASCADE,
        related_name='borrowed_items'
    )
    
    # What was borrowed
    equipment_instance = models.ForeignKey(
        EquipmentInstance,
        on_delete=models.CASCADE,
        related_name='borrowed_items'
    )
    
    # Who borrowed it
    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='borrowed_items'
    )
    
    # Borrowing dates
    borrowed_at = models.DateTimeField(auto_now_add=True)
    return_deadline = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    
    # Return handling
    return_status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.PENDING
    )
    return_notes = models.TextField(
        blank=True,
        help_text="Notes about condition upon return"
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_returns'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-borrowed_at']

    def __str__(self):
        status = "Returned" if self.returned_at else "Active"
        return f"{self.equipment_instance.instance_code} - {self.borrower} ({status})"

    def save(self, *args, **kwargs):
        # Set default return deadline if not provided
        if not self.return_deadline:
            days = self.request.supply.default_borrow_days
            self.return_deadline = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if this item is overdue."""
        if self.returned_at:
            return False
        return timezone.now() > self.return_deadline

    @property
    def days_until_due(self):
        """Days until/since due date. Negative if overdue."""
        if self.returned_at:
            return None
        delta = self.return_deadline - timezone.now()
        return delta.days

    @property
    def overdue_days(self):
        """Number of days overdue. Returns 0 if not overdue."""
        if not self.is_overdue:
            return 0
        delta = timezone.now() - self.return_deadline
        return delta.days

    def process_return(self, received_by, status, notes=''):
        """Process the return of this item."""
        self.returned_at = timezone.now()
        self.return_status = status
        self.return_notes = notes
        self.received_by = received_by
        self.save()
        
        # Update equipment instance status
        instance = self.equipment_instance
        instance.last_returned_at = timezone.now()
        
        if status == self.ReturnStatus.GOOD:
            instance.status = EquipmentInstance.Status.AVAILABLE
        elif status == self.ReturnStatus.DAMAGED:
            instance.status = EquipmentInstance.Status.DAMAGED
            instance.condition_notes = notes
        elif status == self.ReturnStatus.LOST:
            instance.status = EquipmentInstance.Status.LOST
        
        instance.save()
        
        # Check if all items in batch are returned
        self._check_batch_completion()

    def _check_batch_completion(self):
        """Check if all items in the batch have been returned."""
        request = self.request
        
        # Check if individual request is returned (all its borrowed items returned)
        if not request.borrowed_items.filter(returned_at__isnull=True).exists():
            request.status = SupplyRequest.Status.RETURNED
            request.save()
            
        if request.is_batch_request:
            batch_requests = request.batch_requests
            
            # Check if all items in the entire batch are returned
            all_returned = True
            any_returned = False
            
            for req in batch_requests:
                # Count returned items for this request
                items_count = req.borrowed_items.count()
                returned_count = req.borrowed_items.filter(returned_at__isnull=False).count()
                
                if items_count > 0:
                    if returned_count < items_count:
                        all_returned = False
                    if returned_count > 0:
                        any_returned = True
                else:
                    # If no borrowed items (e.g. consumable), check if quest itself is issued/returned
                    if req.status != SupplyRequest.Status.RETURNED:
                        all_returned = False
                    if req.status == SupplyRequest.Status.RETURNED:
                        any_returned = True

            if all_returned:
                batch_requests.update(status=SupplyRequest.Status.RETURNED)
            elif any_returned:
                # Set unreturned items to PARTIALLY_RETURNED to reflect batch state
                batch_requests.filter(
                    status__in=[SupplyRequest.Status.ISSUED, SupplyRequest.Status.APPROVED]
                ).update(status=SupplyRequest.Status.PARTIALLY_RETURNED)


# =============================================================================
# Tracking & Analytics
# =============================================================================

class QRScanLog(models.Model):
    """
    Audit log for every QR scan event.
    
    Tracks who scanned what, when, and for what purpose.
    """
    
    class ScanType(models.TextChoices):
        SCAN = 'scan', 'General Scan'
        ISSUE = 'issue', 'Issue Item'
        RETURN = 'return', 'Return Item'
        INVENTORY = 'inventory', 'Inventory Check'

    # Who scanned
    scanned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='qr_scans'
    )
    
    # What was scanned
    qr_data = models.CharField(max_length=255)
    scan_type = models.CharField(
        max_length=20,
        choices=ScanType.choices,
        default=ScanType.SCAN
    )
    
    # Related objects (optional, for quick lookups)
    supply = models.ForeignKey(
        Supply,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scan_logs'
    )
    equipment_instance = models.ForeignKey(
        EquipmentInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scan_logs'
    )
    supply_request = models.ForeignKey(
        SupplyRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scan_logs'
    )
    
    # Metadata
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Result
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = 'QR Scan Log'
        verbose_name_plural = 'QR Scan Logs'

    def __str__(self):
        return f"{self.scan_type} by {self.scanned_by} at {self.scanned_at}"


class InventoryTransaction(models.Model):
    """
    Logs every stock change for audit and analytics.
    """
    
    class TransactionType(models.TextChoices):
        IN = 'in', 'Stock In'
        OUT = 'out', 'Stock Out'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        TRANSFER = 'transfer', 'Transfer'
        RETURN = 'return', 'Return'
        DAMAGE = 'damage', 'Damage Write-off'
        LOSS = 'loss', 'Loss Write-off'

    supply = models.ForeignKey(
        Supply,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    equipment_instance = models.ForeignKey(
        EquipmentInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    quantity = models.IntegerField(help_text="Positive for in, negative for out")
    
    # Stock levels
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    
    # Reference
    reference_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="PO number, request code, etc."
    )
    supply_request = models.ForeignKey(
        SupplyRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    borrowed_item = models.ForeignKey(
        BorrowedItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    
    # Tracking
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_transactions'
    )
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.supply.name} ({self.quantity:+d})"


class RequestorBorrowerAnalytics(models.Model):
    """
    Aggregated analytics per user for reporting and decision-making.
    
    Updated after each borrowing/return transaction.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Request statistics
    total_requests = models.PositiveIntegerField(default=0)
    approved_requests = models.PositiveIntegerField(default=0)
    rejected_requests = models.PositiveIntegerField(default=0)
    cancelled_requests = models.PositiveIntegerField(default=0)
    
    # Borrowing statistics
    total_borrows = models.PositiveIntegerField(default=0)
    active_borrows = models.PositiveIntegerField(default=0)
    
    # Return performance
    on_time_returns = models.PositiveIntegerField(default=0)
    late_returns = models.PositiveIntegerField(default=0)
    total_overdue_days = models.PositiveIntegerField(default=0)
    
    # Condition history
    good_condition_returns = models.PositiveIntegerField(default=0)
    damaged_returns = models.PositiveIntegerField(default=0)
    lost_items = models.PositiveIntegerField(default=0)
    
    # Calculated scores
    reliability_score = models.FloatField(
        default=100.0,
        help_text="0-100 score based on return performance"
    )
    
    # Timestamps
    last_request_at = models.DateTimeField(null=True, blank=True)
    last_borrow_at = models.DateTimeField(null=True, blank=True)
    last_return_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Analytics'
        verbose_name_plural = 'User Analytics'

    def __str__(self):
        return f"Analytics for {self.user.email}"

    @property
    def approval_rate(self):
        """Percentage of requests approved."""
        if self.total_requests == 0:
            return 0
        return (self.approved_requests / self.total_requests) * 100

    @property
    def on_time_rate(self):
        """Percentage of on-time returns."""
        total_returns = self.on_time_returns + self.late_returns
        if total_returns == 0:
            return 100
        return (self.on_time_returns / total_returns) * 100

    @property
    def damage_rate(self):
        """Percentage of items returned damaged or lost."""
        total_returns = self.good_condition_returns + self.damaged_returns + self.lost_items
        if total_returns == 0:
            return 0
        return ((self.damaged_returns + self.lost_items) / total_returns) * 100

    def recalculate_reliability_score(self):
        """Recalculate reliability score based on all factors."""
        # Weight factors
        ON_TIME_WEIGHT = 0.5
        CONDITION_WEIGHT = 0.3
        OVERDUE_PENALTY = 0.2
        
        # Calculate components
        on_time_component = self.on_time_rate * ON_TIME_WEIGHT
        condition_component = (100 - self.damage_rate) * CONDITION_WEIGHT
        
        # Overdue penalty (max 20 points off)
        avg_overdue = self.total_overdue_days / max(self.late_returns, 1)
        overdue_penalty = min(avg_overdue * 2, 20) * OVERDUE_PENALTY
        
        self.reliability_score = max(0, min(100, 
            on_time_component + condition_component - overdue_penalty
        ))
        self.save()

    def update_from_request(self, request, action):
        """Update analytics based on request action."""
        self.total_requests += 1
        self.last_request_at = timezone.now()
        
        if action == 'approved':
            self.approved_requests += 1
        elif action == 'rejected':
            self.rejected_requests += 1
        elif action == 'cancelled':
            self.cancelled_requests += 1
        
        self.save()

    def update_from_borrow(self, borrowed_item):
        """Update analytics when item is borrowed."""
        self.total_borrows += 1
        self.active_borrows += 1
        self.last_borrow_at = timezone.now()
        self.save()

    def update_from_return(self, borrowed_item):
        """Update analytics when item is returned."""
        self.active_borrows = max(0, self.active_borrows - 1)
        self.last_return_at = timezone.now()
        
        # Track return timing
        if borrowed_item.is_overdue:
            self.late_returns += 1
            self.total_overdue_days += borrowed_item.overdue_days
        else:
            self.on_time_returns += 1
        
        # Track return condition
        if borrowed_item.return_status == BorrowedItem.ReturnStatus.GOOD:
            self.good_condition_returns += 1
        elif borrowed_item.return_status == BorrowedItem.ReturnStatus.DAMAGED:
            self.damaged_returns += 1
        elif borrowed_item.return_status == BorrowedItem.ReturnStatus.LOST:
            self.lost_items += 1
        
        self.save()
        self.recalculate_reliability_score()


class StockAdjustment(models.Model):
    """
    Records stock adjustments for damaged, lost, or inventory corrections.
    
    Created when items are returned damaged/lost or during inventory audits.
    """
    
    class AdjustmentReason(models.TextChoices):
        DAMAGE = 'damage', 'Damage'
        LOSS = 'loss', 'Loss'
        THEFT = 'theft', 'Theft'
        EXPIRED = 'expired', 'Expired'
        CORRECTION = 'correction', 'Inventory Correction'
        OTHER = 'other', 'Other'

    supply = models.ForeignKey(
        Supply,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    equipment_instance = models.ForeignKey(
        EquipmentInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adjustments'
    )
    
    # Adjustment details
    reason = models.CharField(
        max_length=20,
        choices=AdjustmentReason.choices
    )
    quantity = models.IntegerField()
    description = models.TextField()
    
    # Penalty tracking
    is_penalty = models.BooleanField(
        default=False,
        help_text="If True, this adjustment incurs a penalty"
    )
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    responsible_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_adjustments_responsible'
    )
    
    # Related records
    borrowed_item = models.ForeignKey(
        BorrowedItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adjustments'
    )
    
    # Tracking
    adjusted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_adjustments_made'
    )
    adjusted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-adjusted_at']

    def __str__(self):
        return f"{self.get_reason_display()} - {self.supply.name} ({self.quantity})"


# =============================================================================
# Extension Requests
# =============================================================================

class ExtensionRequest(models.Model):
    """
    Allows borrowers to request deadline extensions for borrowed items.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    borrowed_item = models.ForeignKey(
        BorrowedItem,
        on_delete=models.CASCADE,
        related_name='extension_requests'
    )
    
    # Extension details
    requested_days = models.PositiveIntegerField(
        help_text="Number of additional days requested"
    )
    reason = models.TextField(
        help_text="Reason for the extension request"
    )
    
    # Original and new deadlines
    original_deadline = models.DateTimeField()
    new_deadline = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Workflow
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='extension_requests_made'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extension_requests_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Extension for {self.borrowed_item} - {self.requested_days} days"

    def approve(self, reviewed_by, notes=''):
        """Approve the extension request."""
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.new_deadline = self.original_deadline + timedelta(days=self.requested_days)
        self.save()
        
        # Update the borrowed item's deadline
        self.borrowed_item.return_deadline = self.new_deadline
        self.borrowed_item.save()

    def reject(self, reviewed_by, notes=''):
        """Reject the extension request."""
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


# =============================================================================
# Audit Trail
# =============================================================================

class AuditLog(models.Model):
    """
    Comprehensive audit trail for all system actions.
    Records who did what, when, and to what entity.
    """
    
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'
        ISSUE = 'issue', 'Issue'
        RETURN = 'return', 'Return'
        SCAN = 'scan', 'Scan'
        EXPORT = 'export', 'Export'
        IMPORT = 'import', 'Import'

    class EntityType(models.TextChoices):
        USER = 'user', 'User'
        SUPPLY = 'supply', 'Supply'
        CATEGORY = 'category', 'Category'
        INSTANCE = 'instance', 'Equipment Instance'
        REQUEST = 'request', 'Supply Request'
        BORROWED = 'borrowed', 'Borrowed Item'
        EXTENSION = 'extension', 'Extension Request'
        DEPARTMENT = 'department', 'Department'
        SYSTEM = 'system', 'System'

    # Who
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    user_email = models.EmailField(
        help_text="Stored separately in case user is deleted"
    )
    
    # What
    action = models.CharField(max_length=20, choices=ActionType.choices)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    entity_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text="String representation of the entity"
    )
    
    # Details
    description = models.TextField()
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON diff of changes for updates"
    )
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # When
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user_email} {self.action} {self.entity_type} at {self.created_at}"

    @classmethod
    def log(cls, user, action, entity_type, description, entity_id=None, 
            entity_repr='', changes=None, request=None):
        """
        Convenience method to create audit log entries.
        
        Usage:
            AuditLog.log(
                user=request.user,
                action=AuditLog.ActionType.CREATE,
                entity_type=AuditLog.EntityType.REQUEST,
                description="Created supply request REQ-20240101-0001",
                entity_id=supply_request.id,
                entity_repr=str(supply_request),
                request=request
            )
        """
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        return cls.objects.create(
            user=user,
            user_email=user.username if user else 'system',
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_repr=entity_repr[:255] if entity_repr else '',
            description=description,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )


# =============================================================================
# Notifications
# =============================================================================

class Notification(models.Model):
    """
    In-app notifications for users.
    
    Notifications are created when:
    - Request is approved/rejected
    - Item is issued
    - Return deadline approaching
    - Extension approved/rejected
    - Account approved
    - Overdue reminders
    """
    
    class NotificationType(models.TextChoices):
        REQUEST_APPROVED = 'request_approved', 'Request Approved'
        REQUEST_REJECTED = 'request_rejected', 'Request Rejected'
        ITEM_ISSUED = 'item_issued', 'Item Issued'
        ITEM_DUE_SOON = 'item_due_soon', 'Item Due Soon'
        ITEM_OVERDUE = 'item_overdue', 'Item Overdue'
        EXTENSION_APPROVED = 'extension_approved', 'Extension Approved'
        EXTENSION_REJECTED = 'extension_rejected', 'Extension Rejected'
        ACCOUNT_APPROVED = 'account_approved', 'Account Approved'
        ACCOUNT_REJECTED = 'account_rejected', 'Account Rejected'
        NEW_REQUEST = 'new_request', 'New Request'  # For GSO staff
        LOW_STOCK = 'low_stock', 'Low Stock Alert'  # For GSO staff
        SYSTEM = 'system', 'System Notification'

    # Recipient
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional link to related object
    link = models.CharField(
        max_length=255,
        blank=True,
        help_text="URL to navigate when clicked"
    )
    
    # Related objects (optional, for quick lookups)
    related_request = models.ForeignKey(
        'SupplyRequest',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_borrowed_item = models.ForeignKey(
        'BorrowedItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(cls, user, notification_type, title, message, 
                          link='', related_request=None, related_borrowed_item=None):
        """
        Convenience method to create notifications.
        
        Usage:
            Notification.create_notification(
                user=request.user,
                notification_type=Notification.NotificationType.REQUEST_APPROVED,
                title="Request Approved",
                message="Your request REQ-20240101-0001 has been approved.",
                link="/requests/123/",
                related_request=supply_request
            )
        """
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            related_request=related_request,
            related_borrowed_item=related_borrowed_item,
        )

    @classmethod
    def notify_request_approved(cls, supply_request):
        """Create notification when a request is approved."""
        return cls.create_notification(
            user=supply_request.requester,
            notification_type=cls.NotificationType.REQUEST_APPROVED,
            title="Request Approved",
            message=f"Your request for {supply_request.supply.name} ({supply_request.request_code}) has been approved. Please proceed to GSO for pickup.",
            link=f"/requests/{supply_request.id}/",
            related_request=supply_request
        )

    @classmethod
    def notify_request_rejected(cls, supply_request):
        """Create notification when a request is rejected."""
        return cls.create_notification(
            user=supply_request.requester,
            notification_type=cls.NotificationType.REQUEST_REJECTED,
            title="Request Rejected",
            message=f"Your request for {supply_request.supply.name} ({supply_request.request_code}) has been rejected. Reason: {supply_request.review_notes or 'No reason provided.'}",
            link=f"/requests/{supply_request.id}/",
            related_request=supply_request
        )

    @classmethod
    def notify_item_issued(cls, borrowed_item):
        """Create notification when an item is issued."""
        return cls.create_notification(
            user=borrowed_item.borrower,
            notification_type=cls.NotificationType.ITEM_ISSUED,
            title="Item Issued",
            message=f"You have been issued {borrowed_item.equipment_instance.instance_code} ({borrowed_item.equipment_instance.supply.name}). Return by {borrowed_item.return_deadline.strftime('%B %d, %Y')}.",
            link=f"/requests/{borrowed_item.request.id}/",
            related_borrowed_item=borrowed_item
        )

    @classmethod
    def notify_item_due_soon(cls, borrowed_item):
        """Create notification when item is due soon (1-2 days)."""
        days_left = borrowed_item.days_until_due
        return cls.create_notification(
            user=borrowed_item.borrower,
            notification_type=cls.NotificationType.ITEM_DUE_SOON,
            title="Return Reminder",
            message=f"Reminder: {borrowed_item.equipment_instance.instance_code} is due in {days_left} day(s). Please return it by {borrowed_item.return_deadline.strftime('%B %d, %Y')}.",
            link=f"/requests/{borrowed_item.request.id}/",
            related_borrowed_item=borrowed_item
        )

    @classmethod
    def notify_item_overdue(cls, borrowed_item):
        """Create notification when item is overdue."""
        return cls.create_notification(
            user=borrowed_item.borrower,
            notification_type=cls.NotificationType.ITEM_OVERDUE,
            title="Item Overdue!",
            message=f"URGENT: {borrowed_item.equipment_instance.instance_code} is {borrowed_item.overdue_days} day(s) overdue. Please return immediately to avoid penalties.",
            link=f"/requests/{borrowed_item.request.id}/",
            related_borrowed_item=borrowed_item
        )

    @classmethod
    def notify_extension_approved(cls, extension_request):
        """Create notification when extension is approved."""
        return cls.create_notification(
            user=extension_request.requested_by,
            notification_type=cls.NotificationType.EXTENSION_APPROVED,
            title="Extension Approved",
            message=f"Your extension request for {extension_request.borrowed_item.equipment_instance.instance_code} has been approved. New deadline: {extension_request.new_deadline.strftime('%B %d, %Y')}.",
            link=f"/requests/{extension_request.borrowed_item.request.id}/",
            related_borrowed_item=extension_request.borrowed_item
        )

    @classmethod
    def notify_extension_rejected(cls, extension_request):
        """Create notification when extension is rejected."""
        return cls.create_notification(
            user=extension_request.requested_by,
            notification_type=cls.NotificationType.EXTENSION_REJECTED,
            title="Extension Rejected",
            message=f"Your extension request for {extension_request.borrowed_item.equipment_instance.instance_code} has been rejected. {extension_request.review_notes or 'Please return by the original deadline.'}",
            link=f"/requests/{extension_request.borrowed_item.request.id}/",
            related_borrowed_item=extension_request.borrowed_item
        )

    @classmethod
    def notify_account_approved(cls, user):
        """Create notification when user account is approved."""
        return cls.create_notification(
            user=user,
            notification_type=cls.NotificationType.ACCOUNT_APPROVED,
            title="Account Approved",
            message="Welcome! Your account has been approved. You can now start making supply requests.",
            link="/"
        )

    @classmethod
    def notify_new_request_to_gso(cls, supply_request):
        """Notify GSO staff about a new request."""
        from django.db.models import Q
        gso_users = User.objects.filter(
            Q(role=User.Role.GSO_STAFF) | Q(role=User.Role.ADMIN),
            approval_status=User.ApprovalStatus.APPROVED
        )
        
        notifications = []
        for gso_user in gso_users:
            notifications.append(cls.create_notification(
                user=gso_user,
                notification_type=cls.NotificationType.NEW_REQUEST,
                title="New Request",
                message=f"New {supply_request.get_priority_display().lower()} priority request from {supply_request.requester.get_full_name()} for {supply_request.supply.name}.",
                link="/requests/pending/",
                related_request=supply_request
            ))
        return notifications

    @classmethod
    def notify_low_stock(cls, supply):
        """Notify GSO staff about low stock."""
        from django.db.models import Q
        gso_users = User.objects.filter(
            Q(role=User.Role.GSO_STAFF) | Q(role=User.Role.ADMIN),
            approval_status=User.ApprovalStatus.APPROVED
        )
        
        notifications = []
        for gso_user in gso_users:
            notifications.append(cls.create_notification(
                user=gso_user,
                notification_type=cls.NotificationType.LOW_STOCK,
                title="Low Stock Alert",
                message=f"{supply.name} is running low ({supply.quantity} {supply.unit} remaining).",
                link=f"/supplies/{supply.id}/"
            ))
        return notifications
