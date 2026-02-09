"""
PDF Generation Utilities for ERP System
Provides reusable functions for generating PDF reports
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime


class PDFGenerator:
    """Base class for PDF generation with common styling"""
    
    def __init__(self, buffer, title="Report", company=None):
        self.buffer = buffer
        self.title = title
        self.company = company
        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.elements = []
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Company header style
        self.styles.add(ParagraphStyle(
            name='CompanyHeader',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            alignment=TA_CENTER,
        ))
        
    def add_text(self, text, style='Normal', align=None, color=None, bold=False):
        """Add a text paragraph with optional styling"""
        # Get base style
        if style in self.styles:
            para_style = self.styles[style]
        else:
            para_style = self.styles['Normal']
            
        # Clone style if we need to modify it (to avoid affecting other paragraphs)
        if align or color:
            # Create a unique name to avoid conflicts if we were caching, 
            # but here we just create a new instance effectively
            para_style = ParagraphStyle(
                name=f'{style}_custom_{len(self.elements)}',
                parent=para_style
            )
            
            if align:
                if align.upper() == 'CENTER':
                    para_style.alignment = TA_CENTER
                elif align.upper() == 'RIGHT':
                    para_style.alignment = TA_RIGHT
                elif align.upper() == 'LEFT':
                    para_style.alignment = TA_LEFT
                    
            if color:
                para_style.textColor = colors.HexColor(color)
        
        # Handle bold using HTML tag if requested
        content = text
        if bold:
            content = f"<b>{content}</b>"
            
        self.elements.append(Paragraph(content, para_style))

    def add_company_header(self):
        """Add company name and report title"""
        if self.company:
            company_name = Paragraph(
                f"<b>{self.company.name}</b>",
                self.styles['CompanyHeader']
            )
            self.elements.append(company_name)
            
        title = Paragraph(self.title, self.styles['CustomTitle'])
        self.elements.append(title)
        
        # Add generation date
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        subtitle = Paragraph(
            f"Generated on {date_str}",
            self.styles['CustomSubtitle']
        )
        self.elements.append(subtitle)
        
    def add_spacer(self, height=0.2):
        """Add vertical space"""
        self.elements.append(Spacer(1, height * inch))
        
    def create_table(self, data, col_widths=None, style=None):
        """Create a formatted table"""
        if style is None:
            style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Body styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(style)
        return table
        
    def add_summary_section(self, title, data):
        """Add a summary section with key-value pairs"""
        self.add_spacer(0.3)
        
        # Section title
        section_title = Paragraph(
            f"<b>{title}</b>",
            self.styles['Heading2']
        )
        self.elements.append(section_title)
        self.add_spacer(0.1)
        
        # Create summary table
        summary_data = [[k, v] for k, v in data.items()]
        summary_table = self.create_table(
            summary_data,
            col_widths=[3*inch, 3*inch],
            style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ])
        )
        self.elements.append(summary_table)
        
    def build(self):
        """Build the PDF document"""
        self.doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer
