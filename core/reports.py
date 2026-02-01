"""
PDF Report Generation Module for Smart Supply

Uses reportlab for PDF generation. Install with: pip install reportlab
"""
import io
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.utils import timezone

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def get_styles():
    """Get custom styles for reports."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0f172a'),
    ))
    
    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748b'),
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#1e293b'),
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    ))
    
    return styles


def create_table_style():
    """Create standard table style."""
    return TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#334155')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])


def generate_inventory_report(supplies, filename="inventory_report.pdf"):
    """
    Generate inventory status report.
    
    Args:
        supplies: QuerySet of Supply objects
        filename: Output filename
    
    Returns:
        HttpResponse with PDF
    """
    if not HAS_REPORTLAB:
        return HttpResponse("reportlab not installed", status=500)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = get_styles()
    elements = []
    
    # Title
    elements.append(Paragraph("Inventory Status Report", styles['ReportTitle']))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles['ReportSubtitle']
    ))
    elements.append(Spacer(1, 20))
    
    # Summary stats
    total_items = supplies.count()
    low_stock = sum(1 for s in supplies if s.is_low_stock)
    out_of_stock = sum(1 for s in supplies if s.is_out_of_stock)
    
    summary_data = [
        ['Total Items', 'Low Stock', 'Out of Stock'],
        [str(total_items), str(low_stock), str(out_of_stock)],
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#86efac')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Inventory table
    elements.append(Paragraph("Detailed Inventory", styles['SectionTitle']))
    
    data = [['Item Name', 'Category', 'Quantity', 'Min Stock', 'Status', 'Unit']]
    for supply in supplies:
        status = 'In Stock'
        if supply.is_out_of_stock:
            status = 'OUT OF STOCK'
        elif supply.is_low_stock:
            status = 'Low Stock'
        
        data.append([
            supply.name[:30],
            supply.category.name[:20],
            str(supply.quantity),
            str(supply.min_stock_level),
            status,
            supply.unit,
        ])
    
    table = Table(data, colWidths=[2*inch, 1.3*inch, 0.8*inch, 0.8*inch, 1*inch, 0.6*inch])
    table.setStyle(create_table_style())
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_borrowing_report(borrowed_items, user=None, filename="borrowing_report.pdf"):
    """
    Generate borrowing history report.
    
    Args:
        borrowed_items: QuerySet of BorrowedItem objects
        user: Optional user to filter by
        filename: Output filename
    
    Returns:
        HttpResponse with PDF
    """
    if not HAS_REPORTLAB:
        return HttpResponse("reportlab not installed", status=500)
    
    buffer = io.BytesIO()
    # Use landscape Letter for maximum horizontal space
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = get_styles()
    elements = []
    
    # Title
    title = "Borrowing History Report"
    subtitle = "Smart Supply Management System"
    timestamp = f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    
    # If it's a specific user's report (not an admin viewing all), add their name
    if user and user.role != 'admin':
        title = f"Borrowing History - {user.get_full_name()}"
    
    elements.append(Paragraph(title, styles['ReportTitle']))
    elements.append(Paragraph(subtitle, styles['ReportSubtitle']))
    elements.append(Paragraph(timestamp, styles['ReportSubtitle']))
    elements.append(Spacer(1, 10))
    
    # Summary
    total = borrowed_items.count()
    active = borrowed_items.filter(returned_at__isnull=True).count()
    overdue = sum(1 for b in borrowed_items if b.is_overdue)
    
    summary_data = [
        ['Total Borrows', 'Currently Active', 'Overdue'],
        [str(total), str(active), str(overdue)],
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#eef2ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#a5b4fc')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Borrowing table
    elements.append(Paragraph("Detailed Transaction History", styles['SectionTitle']))
    
    # Create cell style for table content to allow wrapping
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
    )
    
    data = [['Equipment', 'Borrower', 'Borrowed', 'Due Date', 'Returned', 'Status']]
    for item in borrowed_items[:200]:  # Increased limit for systematic reports
        status = item.get_return_status_display() if item.returned_at else ('Overdue' if item.is_overdue else 'Active')
        
        # Use Paragraphs in cells that need wrapping
        data.append([
            Paragraph(item.equipment_instance.instance_code, cell_style),
            Paragraph(item.borrower.get_full_name(), cell_style),
            item.borrowed_at.strftime('%m/%d/%Y'),
            item.return_deadline.strftime('%m/%d/%Y'),
            item.returned_at.strftime('%m/%d/%Y') if item.returned_at else '-',
            Paragraph(status, cell_style),
        ])
    
    # Total width for landscape letter is 11.0 inches. With 0.5 inch margins, we have 10.0 inches.
    table = Table(data, colWidths=[1.2*inch, 2.0*inch, 1.1*inch, 1.1*inch, 1.1*inch, 3.5*inch])
    table.setStyle(create_table_style())
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_user_analytics_report(analytics_list, filename="user_analytics_report.pdf"):
    """
    Generate user analytics report.
    
    Args:
        analytics_list: QuerySet of RequestorBorrowerAnalytics objects
        filename: Output filename
    
    Returns:
        HttpResponse with PDF
    """
    if not HAS_REPORTLAB:
        return HttpResponse("reportlab not installed", status=500)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = get_styles()
    elements = []
    
    # Title
    elements.append(Paragraph("User Analytics Report", styles['ReportTitle']))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles['ReportSubtitle']
    ))
    elements.append(Spacer(1, 20))
    
    # Analytics table
    data = [['User', 'Department', 'Total Borrows', 'On-Time Rate', 'Reliability Score']]
    for a in analytics_list:
        data.append([
            a.user.get_full_name()[:25],
            a.user.department.name[:15] if a.user.department else 'N/A',
            str(a.total_borrows),
            f"{a.on_time_rate:.1f}%",
            f"{a.reliability_score:.1f}",
        ])
    
    table = Table(data, colWidths=[1.8*inch, 1.2*inch, 1*inch, 1*inch, 1.2*inch])
    table.setStyle(create_table_style())
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_qr_sheet(instances, filename="qr_codes.pdf"):
    """
    Generate a printable sheet of QR codes.
    
    Args:
        instances: QuerySet of EquipmentInstance objects
        filename: Output filename
    
    Returns:
        HttpResponse with PDF
    """
    if not HAS_REPORTLAB:
        return HttpResponse("reportlab not installed", status=500)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = get_styles()
    elements = []
    
    # Title
    elements.append(Paragraph("Equipment QR Codes", styles['ReportTitle']))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y')}",
        styles['ReportSubtitle']
    ))
    elements.append(Spacer(1, 20))
    
    # QR codes grid (3 per row)
    qr_data = []
    row = []
    
    for i, instance in enumerate(instances):
        if instance.qr_code:
            cell_content = []
            try:
                img = Image(instance.qr_code.path, width=1.5*inch, height=1.5*inch)
                cell_content.append(img)
            except:
                cell_content.append(Paragraph("QR N/A", styles['Normal']))
            
            cell_content.append(Spacer(1, 5))
            cell_content.append(Paragraph(
                f"<b>{instance.instance_code}</b>",
                ParagraphStyle('QRLabel', fontSize=10, alignment=TA_CENTER)
            ))
            cell_content.append(Paragraph(
                instance.supply.name[:25],
                ParagraphStyle('QRDesc', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
            ))
            
            row.append(cell_content)
            
            if len(row) == 3:
                qr_data.append(row)
                row = []
    
    if row:  # Add remaining items
        while len(row) < 3:
            row.append('')
        qr_data.append(row)
    
    if qr_data:
        table = Table(qr_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No QR codes available. Generate QR codes first.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
