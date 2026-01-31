"""
Management command to seed sample data for testing.
Run with: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid

from core.models import (
    Department,
    User,
    SupplyCategory,
    Supply,
    EquipmentInstance,
    SupplyRequest,
    BorrowedItem,
    RequestorBorrowerAnalytics,
)


class Command(BaseCommand):
    help = 'Seeds the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self._clear_data()

        self.stdout.write('Creating departments...')
        departments = self._create_departments()

        self.stdout.write('Creating users...')
        users = self._create_users(departments)

        self.stdout.write('Creating supply categories...')
        categories = self._create_categories()

        self.stdout.write('Creating supplies...')
        supplies = self._create_supplies(categories, users['gso_staff'])

        self.stdout.write('Creating equipment instances...')
        instances = self._create_equipment_instances(supplies)

        self.stdout.write('Creating sample requests...')
        self._create_sample_requests(users, supplies, instances)

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write(f'\nTest accounts:')
        self.stdout.write(f'  Admin: admin@smartsupply.local / admin123')
        self.stdout.write(f'  GSO Staff: gso@smartsupply.local / gso123')
        self.stdout.write(f'  Department User: user@smartsupply.local / user123')

    def _clear_data(self):
        BorrowedItem.objects.all().delete()
        SupplyRequest.objects.all().delete()
        EquipmentInstance.objects.all().delete()
        Supply.objects.all().delete()
        SupplyCategory.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Department.objects.all().delete()

    def _create_departments(self):
        departments = {}
        dept_data = [
            ('IT', 'Information Technology', 'Manages all IT infrastructure and support'),
            ('HR', 'Human Resources', 'Handles recruitment and employee management'),
            ('FIN', 'Finance', 'Manages company finances and budgeting'),
            ('OPS', 'Operations', 'Manages day-to-day operations'),
            ('MKT', 'Marketing', 'Handles marketing and communications'),
            ('GSO', 'General Services Office', 'Manages supplies and equipment'),
        ]
        
        for code, name, desc in dept_data:
            dept, _ = Department.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
            departments[code] = dept
        
        return departments

    def _create_users(self, departments):
        users = {}
        
        # GSO Staff
        gso_staff, created = User.objects.get_or_create(
            email='gso@smartsupply.local',
            defaults={
                'first_name': 'Maria',
                'last_name': 'Santos',
                'role': User.Role.GSO_STAFF,
                'approval_status': User.ApprovalStatus.APPROVED,
                'department': departments['GSO'],
                'phone': '+63 917 123 4567',
            }
        )
        if created:
            gso_staff.set_password('gso123')
            gso_staff.save()
        users['gso_staff'] = gso_staff
        
        # Department users
        dept_users_data = [
            ('user@smartsupply.local', 'Juan', 'Dela Cruz', 'IT', 'user123'),
            ('jsmith@smartsupply.local', 'John', 'Smith', 'HR', 'user123'),
            ('agarcia@smartsupply.local', 'Ana', 'Garcia', 'FIN', 'user123'),
        ]
        
        for email, first, last, dept, pwd in dept_users_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': User.Role.DEPARTMENT_USER,
                    'approval_status': User.ApprovalStatus.APPROVED,
                    'department': departments[dept],
                }
            )
            if created:
                user.set_password(pwd)
                user.save()
            users[email] = user
        
        # Pending user
        pending_user, created = User.objects.get_or_create(
            email='pending@smartsupply.local',
            defaults={
                'first_name': 'New',
                'last_name': 'Employee',
                'role': User.Role.DEPARTMENT_USER,
                'approval_status': User.ApprovalStatus.PENDING,
                'department': departments['OPS'],
            }
        )
        if created:
            pending_user.set_password('pending123')
            pending_user.save()
        users['pending'] = pending_user
        
        return users

    def _create_categories(self):
        categories = {}
        cat_data = [
            ('Electronics', True, 'laptop', 'Electronic equipment like laptops and projectors'),
            ('Office Equipment', True, 'printer', 'Office machines and tools'),
            ('Furniture', True, 'chair', 'Office furniture items'),
            ('Office Supplies', False, 'pencil', 'Consumable office supplies'),
            ('Cleaning Supplies', False, 'spray', 'Cleaning materials and chemicals'),
        ]
        
        for name, is_material, icon, desc in cat_data:
            cat, _ = SupplyCategory.objects.get_or_create(
                name=name,
                defaults={
                    'is_material': is_material,
                    'icon': icon,
                    'description': desc,
                }
            )
            categories[name] = cat
        
        return categories

    def _create_supplies(self, categories, created_by):
        supplies = {}
        supply_data = [
            # Electronics (Equipment)
            ('ThinkPad L14 Laptop', 'Electronics', 10, 3, 7, 'pcs'),
            ('Dell P2422H Monitor', 'Electronics', 15, 5, 7, 'pcs'),
            ('Epson EcoTank L3210', 'Electronics', 5, 2, 14, 'pcs'),
            ('Logitech Webcam C920', 'Electronics', 8, 3, 7, 'pcs'),
            
            # Office Equipment
            ('Projector Epson EB-S41', 'Office Equipment', 3, 1, 3, 'pcs'),
            ('Whiteboard 4x6 ft', 'Office Equipment', 5, 2, 7, 'pcs'),
            ('Extension Cord 10m', 'Office Equipment', 20, 5, 3, 'pcs'),
            
            # Furniture
            ('Office Chair Ergonomic', 'Furniture', 30, 10, 30, 'pcs'),
            ('Standing Desk', 'Furniture', 10, 3, 30, 'pcs'),
            
            # Office Supplies (Consumables)
            ('A4 Bond Paper', 'Office Supplies', 500, 100, 3, 'ream'),
            ('Ballpoint Pen (Black)', 'Office Supplies', 200, 50, 3, 'pcs'),
            ('Whiteboard Marker', 'Office Supplies', 100, 30, 3, 'pcs'),
            ('Sticky Notes 3x3', 'Office Supplies', 150, 40, 3, 'pack'),
            
            # Cleaning Supplies (Consumables)
            ('Alcohol 70% 500ml', 'Cleaning Supplies', 50, 15, 3, 'bottle'),
            ('Hand Soap 500ml', 'Cleaning Supplies', 30, 10, 3, 'bottle'),
        ]
        
        for name, cat_name, qty, min_stock, borrow_days, unit in supply_data:
            supply, _ = Supply.objects.get_or_create(
                name=name,
                category=categories[cat_name],
                defaults={
                    'quantity': qty,
                    'min_stock_level': min_stock,
                    'default_borrow_days': borrow_days,
                    'unit': unit,
                    'created_by': created_by,
                    'is_consumable': not categories[cat_name].is_material,
                }
            )
            supplies[name] = supply
        
        return supplies

    def _create_equipment_instances(self, supplies):
        instances = {}
        equipment_items = [
            ('ThinkPad L14 Laptop', 'LAPTOP', 5),
            ('Dell P2422H Monitor', 'MON', 8),
            ('Projector Epson EB-S41', 'PROJ', 3),
            ('Office Chair Ergonomic', 'CHAIR', 10),
        ]
        
        for supply_name, prefix, count in equipment_items:
            supply = supplies.get(supply_name)
            if supply and supply.category.is_material:
                for i in range(1, count + 1):
                    instance_code = f"{prefix}-{i:02d}"
                    instance, _ = EquipmentInstance.objects.get_or_create(
                        instance_code=instance_code,
                        defaults={
                            'supply': supply,
                            'serial_number': f"SN{prefix}{i:06d}",
                            'status': EquipmentInstance.Status.AVAILABLE,
                            'acquired_date': timezone.now().date() - timedelta(days=365),
                            'warranty_expiry': timezone.now().date() + timedelta(days=365),
                        }
                    )
                    instances[instance_code] = instance
        
        # Mark some as borrowed/maintenance for testing
        if 'LAPTOP-01' in instances:
            instances['LAPTOP-01'].status = EquipmentInstance.Status.BORROWED
            instances['LAPTOP-01'].save()
        if 'PROJ-02' in instances:
            instances['PROJ-02'].status = EquipmentInstance.Status.MAINTENANCE
            instances['PROJ-02'].condition_notes = 'Lamp replacement scheduled'
            instances['PROJ-02'].save()
        
        return instances

    def _create_sample_requests(self, users, supplies, instances):
        requester = users.get('user@smartsupply.local')
        gso_staff = users.get('gso_staff')
        
        if not requester or not gso_staff:
            return
        
        # Create analytics record for requester
        analytics, _ = RequestorBorrowerAnalytics.objects.get_or_create(user=requester)
        
        # Sample pending request
        SupplyRequest.objects.get_or_create(
            requester=requester,
            supply=supplies['ThinkPad L14 Laptop'],
            status=SupplyRequest.Status.PENDING,
            defaults={
                'purpose': 'Need a laptop for the upcoming project presentation',
                'priority': SupplyRequest.Priority.NORMAL,
                'needed_by': timezone.now() + timedelta(days=2),
            }
        )
        
        # Sample approved request
        approved_req, created = SupplyRequest.objects.get_or_create(
            requester=requester,
            supply=supplies['Projector Epson EB-S41'],
            status=SupplyRequest.Status.APPROVED,
            defaults={
                'purpose': 'Department meeting presentation',
                'priority': SupplyRequest.Priority.HIGH,
                'reviewed_by': gso_staff,
                'reviewed_at': timezone.now() - timedelta(hours=2),
            }
        )
        if created:
            approved_req.generate_qr_code()
            approved_req.save()
        
        # Sample issued request with borrowed item
        issued_req, created = SupplyRequest.objects.get_or_create(
            requester=requester,
            supply=supplies['ThinkPad L14 Laptop'],
            status=SupplyRequest.Status.ISSUED,
            defaults={
                'purpose': 'Work from home equipment',
                'priority': SupplyRequest.Priority.NORMAL,
                'reviewed_by': gso_staff,
                'reviewed_at': timezone.now() - timedelta(days=5),
                'issued_by': gso_staff,
                'issued_at': timezone.now() - timedelta(days=5),
            }
        )
        
        if created and 'LAPTOP-01' in instances:
            # Create borrowed item
            borrowed, _ = BorrowedItem.objects.get_or_create(
                request=issued_req,
                equipment_instance=instances['LAPTOP-01'],
                borrower=requester,
                defaults={
                    'return_deadline': timezone.now() - timedelta(days=2),  # Overdue!
                }
            )
            
            # Update instance
            instances['LAPTOP-01'].status = EquipmentInstance.Status.BORROWED
            instances['LAPTOP-01'].last_borrowed_by = requester
            instances['LAPTOP-01'].last_borrowed_at = timezone.now() - timedelta(days=5)
            instances['LAPTOP-01'].save()
            
            # Update analytics
            analytics.total_borrows = 1
            analytics.active_borrows = 1
            analytics.save()
        
        # Batch request example
        batch_id = uuid.uuid4()
        for supply_name in ['A4 Bond Paper', 'Ballpoint Pen (Black)', 'Sticky Notes 3x3']:
            SupplyRequest.objects.get_or_create(
                requester=requester,
                supply=supplies[supply_name],
                batch_group_id=batch_id,
                status=SupplyRequest.Status.PENDING,
                defaults={
                    'purpose': 'Monthly office supplies for IT department',
                    'priority': SupplyRequest.Priority.NORMAL,
                    'quantity': 5 if 'Paper' in supply_name else 10,
                }
            )
