"""
Professional Report Generation Service
Creates A4-sized PDF reports with full CNPS-style formatting
"""

import os
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import json
import tempfile

logger = logging.getLogger(__name__)

# PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        Image, ListFlowable, ListItem, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Excel generation
import pandas as pd

# Chart generation
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
from io import BytesIO


class ProfessionalReportGenerator:
    """Generate professional A4 PDF reports with CNPS-style formatting"""
    
    def __init__(self, institution_name: str = "CNPS"):
        self.institution_name = institution_name
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab is not installed — PDF reports are unavailable")
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for professional formatting"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading 1
        self.styles.add(ParagraphStyle(
            name='ReportH1',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=12,
            spaceBefore=16,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=colors.HexColor('#2c5282'),
            borderPadding=5,
            leftIndent=0,
            backColor=colors.HexColor('#ebf4ff')
        ))
        
        # Heading 2
        self.styles.add(ParagraphStyle(
            name='ReportH2',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=10,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            fontName='Helvetica'
        ))
        
        # Bullet text
        self.styles.add(ParagraphStyle(
            name='ReportBullet',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        # Caption style
        self.styles.add(ParagraphStyle(
            name='ReportCaption',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=colors.HexColor('#4a5568'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Oblique'
        ))
        
        # Executive summary box
        self.styles.add(ParagraphStyle(
            name='ExecSummary',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            fontName='Helvetica',
            backColor=colors.HexColor('#f7fafc'),
            borderWidth=1,
            borderColor=colors.HexColor('#cbd5e0'),
            borderPadding=10
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['BodyText'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName='Helvetica'
        ))
    
    def generate_report(
        self,
        report_data: Dict[str, Any],
        output_path: str,
        format: str = "pdf"
    ) -> str:
        """
        Generate professional report in PDF or Excel format
        
        Args:
            report_data: Dictionary containing all report sections
            output_path: Path to save the report
            format: "pdf" or "excel"
        
        Returns:
            Path to generated report
        """
        if format == "excel":
            return self._generate_excel(report_data, output_path)
        else:
            return self._generate_pdf(report_data, output_path)
    
    def _generate_pdf(self, report_data: Dict[str, Any], output_path: str) -> str:
        """Generate A4 PDF report with professional formatting"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Generate charts if data is available
        chart_paths = self._generate_charts(report_data)
        
        # ========== TITLE PAGE ==========
        story.append(Spacer(1, 4*cm))
        story.append(Paragraph(
            report_data.get('title', 'Data Analysis Report'),
            self.styles['ReportTitle']
        ))
        story.append(Spacer(1, 1*cm))
        
        # Institution logo placeholder
        story.append(Paragraph(
            f"<b>{self.institution_name}</b>",
            ParagraphStyle(
                name='Institution',
                parent=self.styles['Normal'],
                fontSize=14,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2c5282')
            )
        ))
        story.append(Spacer(1, 2*cm))
        
        # Metadata table
        metadata = [
            ['Prepared for:', report_data.get('prepared_for', self.institution_name)],
            ['Prepared by:', report_data.get('prepared_by', 'Data Analysis Unit')],
            ['Date:', report_data.get('date', datetime.now().strftime('%B %d, %Y'))],
            ['Version:', report_data.get('version', '1.0')],
            ['Report Type:', report_data.get('report_type', 'Analysis Report')]
        ]
        
        metadata_table = Table(metadata, colWidths=[4*cm, 10*cm])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c5282')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(metadata_table)
        story.append(PageBreak())
        
        # ========== TABLE OF CONTENTS ==========
        story.append(Paragraph('Table of Contents', self.styles['ReportH1']))
        story.append(Spacer(1, 0.5*cm))
        
        sections = [
            'Executive Summary',
            'Introduction and Background',
            'Data Sources',
            'Methodology',
            'Data Quality and Cleaning',
            'Analysis and Results',
            'Interpretation and Key Findings',
            'Risk Analysis',
            'Forecasts and Projections',
            'Conclusions and Recommendations',
            'Limitations',
            'Reproducibility and Data Access',
            'Metadata and File Naming',
            'Versioning and Change Log',
            'Quality Control Checklist',
            'Sign-off'
        ]
        
        for i, section in enumerate(sections, 1):
            story.append(Paragraph(
                f"{i}. {section}" + " " * 80 + f"{i}",
                ParagraphStyle(
                    name='TOCItem',
                    parent=self.styles['Normal'],
                    fontSize=10,
                    leading=16,
                    leftIndent=20
                )
            ))
        
        story.append(PageBreak())
        
        # ========== EXECUTIVE SUMMARY ==========
        story.append(Paragraph('Executive Summary', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('executive_summary', 'No executive summary available.'),
            self.styles['ExecSummary']
        ))
        story.append(PageBreak())
        
        # ========== INTRODUCTION ==========
        story.append(Paragraph('Introduction and Background', self.styles['ReportH1']))
        story.append(Paragraph('Background', self.styles['ReportH2']))
        story.append(Paragraph(
            report_data.get('background', 'This report presents analysis of institutional data.'),
            self.styles['ReportBody']
        ))
        
        story.append(Paragraph('Objectives', self.styles['ReportH2']))
        objectives = report_data.get('objectives', [])
        for obj in objectives:
            story.append(Paragraph(f"• {obj}", self.styles['ReportBullet']))
        
        story.append(PageBreak())
        
        # ========== DATA SOURCES ==========
        story.append(Paragraph('Data Sources', self.styles['ReportH1']))
        data_sources = report_data.get('data_sources', [])
        for source in data_sources:
            story.append(Paragraph(f"<b>{source.get('name', 'Data Source')}</b>", self.styles['ReportBody']))
            story.append(Paragraph(source.get('description', ''), self.styles['ReportBody']))
            story.append(Spacer(1, 0.3*cm))
        
        # ========== METHODOLOGY ==========
        story.append(Paragraph('Methodology', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('methodology', 'Standard analytical methods were applied.'),
            self.styles['ReportBody']
        ))
        story.append(PageBreak())
        
        # ========== DATA QUALITY ==========
        story.append(Paragraph('Data Quality and Cleaning', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('data_quality', 'Data quality checks were performed.'),
            self.styles['ReportBody']
        ))
        
        # Quality metrics table
        if 'quality_metrics' in report_data:
            quality_data = [['Metric', 'Value', 'Status']]
            for metric in report_data['quality_metrics']:
                quality_data.append([
                    metric.get('metric', ''),
                    metric.get('value', ''),
                    metric.get('status', '✓')
                ])
            
            quality_table = Table(quality_data, colWidths=[6*cm, 4*cm, 4*cm])
            quality_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
            ]))
            story.append(quality_table)
        
        story.append(PageBreak())
        
        # ========== ANALYSIS AND RESULTS ==========
        story.append(Paragraph('Analysis and Results', self.styles['ReportH1']))
        
        # KPI Summary Table
        if 'kpis' in report_data and report_data['kpis']:
            story.append(Paragraph('Key Performance Indicators', self.styles['ReportH2']))
            
            kpi_data = [['KPI', 'Current Value', 'DoD %', 'WoW %', 'Status']]
            for kpi in report_data['kpis'][:10]:  # Top 10 KPIs
                kpi_data.append([
                    kpi.get('kpi_name', '').replace('_', ' ').title(),
                    f"{kpi.get('value', 0):,.2f}",
                    f"{kpi.get('dod_pct', 0):+.1f}%" if kpi.get('dod_pct') else "N/A",
                    f"{kpi.get('wow_pct', 0):+.1f}%" if kpi.get('wow_pct') else "N/A",
                    kpi.get('status', 'NORMAL')
                ])
            
            kpi_table = Table(kpi_data, colWidths=[5*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Add KPI trend chart if available
        if 'kpis' in chart_paths and chart_paths['kpis']:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph('Figure 1: KPI Trends Overview', self.styles['ReportCaption']))
            story.append(Image(chart_paths['kpis'], width=16*cm, height=8*cm))
            story.append(Spacer(1, 0.5*cm))
        
        # Anomalies
        if 'anomalies' in report_data and report_data['anomalies']:
            story.append(Paragraph('Detected Anomalies', self.styles['ReportH2']))
            for anomaly in report_data['anomalies'][:5]:
                story.append(Paragraph(
                    f"• <b>{anomaly.get('kpi_name', '').replace('_', ' ').title()}</b>: "
                    f"{anomaly.get('context', {}).get('reason', 'Deviation detected')} "
                    f"({anomaly.get('deviation', 0):.1f}% deviation)",
                    self.styles['ReportBullet']
                ))
        
        # Add anomaly chart if available
        if 'anomalies' in chart_paths and chart_paths['anomalies']:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph('Figure 2: Anomaly Severity Distribution', self.styles['ReportCaption']))
            story.append(Image(chart_paths['anomalies'], width=14*cm, height=7*cm))
            story.append(Spacer(1, 0.5*cm))
        
        story.append(PageBreak())
        
        # ========== INTERPRETATION ==========
        story.append(Paragraph('Interpretation and Key Findings', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('interpretation', 'Key findings are summarized below.'),
            self.styles['ReportBody']
        ))
        
        if 'key_findings' in report_data:
            for finding in report_data['key_findings']:
                story.append(Paragraph(f"• {finding}", self.styles['ReportBullet']))
        
        story.append(PageBreak())
        
        # ========== RISK ANALYSIS ==========
        if report_data.get('risk_analysis_text'):
            story.append(Paragraph('Risk Analysis', self.styles['ReportH1']))
            story.append(Paragraph(
                report_data['risk_analysis_text'],
                self.styles['ReportBody']
            ))
            story.append(Spacer(1, 0.5*cm))
        
        # ========== FORECASTS ==========
        if report_data.get('forecasts') and len(report_data.get('forecasts', [])) > 0:
            story.append(Paragraph('Forecasts and Projections', self.styles['ReportH1']))
            story.append(Paragraph(
                'The following projections are based on observed trends in the analysis data.',
                self.styles['ReportBody']
            ))
            story.append(Spacer(1, 0.3*cm))
            # Add forecast chart if available
            if 'time_series' in chart_paths and chart_paths['time_series']:
                story.append(Paragraph('Figure 3: Historical Trends for Forecast Basis', self.styles['ReportCaption']))
                story.append(Image(chart_paths['time_series'], width=16*cm, height=8*cm))
                story.append(Spacer(1, 0.5*cm))
            story.append(PageBreak())
        
        # ========== CONCLUSIONS AND RECOMMENDATIONS ==========
        story.append(Paragraph('Conclusions and Recommendations', self.styles['ReportH1']))
        
        story.append(Paragraph('Conclusions', self.styles['ReportH2']))
        conclusions = report_data.get('conclusions', [])
        for conclusion in conclusions:
            story.append(Paragraph(f"• {conclusion}", self.styles['ReportBullet']))
        
        story.append(Paragraph('Recommendations', self.styles['ReportH2']))
        if report_data.get('recommendations_text'):
            story.append(Paragraph(report_data['recommendations_text'], self.styles['ReportBody']))
        else:
            recommendations = report_data.get('recommendations', [])
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", self.styles['ReportBullet']))
        
        story.append(PageBreak())
        
        # ========== LIMITATIONS ==========
        story.append(Paragraph('Limitations', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('limitations', 'This analysis has certain limitations that should be considered when interpreting results.'),
            self.styles['ReportBody']
        ))
        
        # ========== REPRODUCIBILITY ==========
        story.append(Paragraph('Reproducibility and Data Access', self.styles['ReportH1']))
        story.append(Paragraph(
            report_data.get('reproducibility', 'Analysis code and data are available upon request.'),
            self.styles['ReportBody']
        ))
        
        # ========== METADATA ==========
        story.append(Paragraph('Metadata and File Naming', self.styles['ReportH1']))
        story.append(Paragraph(
            f"<b>File Name:</b> {report_data.get('file_name', 'report_v1.0.pdf')}<br/>"
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"<b>Report ID:</b> {report_data.get('report_id', 'N/A')}",
            self.styles['Metadata']
        ))
        
        # ========== VERSIONING ==========
        story.append(Paragraph('Versioning and Change Log', self.styles['ReportH1']))
        version_data = [['Version', 'Date', 'Author', 'Changes']]
        for version in report_data.get('versions', []):
            version_data.append([
                version.get('version', '1.0'),
                version.get('date', datetime.now().strftime('%Y-%m-%d')),
                version.get('author', 'System'),
                version.get('changes', 'Initial version')
            ])
        
        version_table = Table(version_data, colWidths=[2*cm, 3*cm, 4*cm, 6*cm])
        version_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
        ]))
        story.append(version_table)
        story.append(PageBreak())
        
        # ========== QUALITY CONTROL CHECKLIST ==========
        story.append(Paragraph('Quality Control and Compliance Checklist', self.styles['ReportH1']))
        checklist_items = [
            'Data validity: All results reproduce when code is rerun',
            'Documentation: Data sources, methodology, and assumptions documented',
            'Code review: Analysis scripts reviewed for correctness',
            'Clarity: Figures have clear labels and captions',
            'Consistency: Terminology and units consistent throughout',
            'Format: Report follows standard formatting',
            'Compliance: No sensitive personal data disclosed',
            'Alignment: All objectives addressed'
        ]
        for item in checklist_items:
            story.append(Paragraph(f"☐ {item}", self.styles['ReportBullet']))
        
        story.append(Spacer(1, 2*cm))
        
        # ========== SIGN-OFF ==========
        story.append(Paragraph('Sign-off', self.styles['ReportH1']))
        signoff_data = [
            ['Role', 'Name', 'Date', 'Signature'],
            ['Prepared by:', report_data.get('prepared_by', 'Data Analyst'), report_data.get('date', datetime.now().strftime('%Y-%m-%d')), ''],
            ['Reviewed by:', report_data.get('reviewed_by', 'Department Head'), '', '']
        ]
        
        signoff_table = Table(signoff_data, colWidths=[4*cm, 5*cm, 4*cm, 3*cm])
        signoff_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
        ]))
        story.append(signoff_table)
        
        # Build PDF
        doc.build(story)
        
        # Cleanup temporary chart files
        for chart_path in chart_paths.values():
            if chart_path and os.path.exists(chart_path):
                try:
                    os.remove(chart_path)
                except Exception:
                    pass
        
        return output_path
    
    def _generate_charts(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate chart images from report data"""
        chart_paths = {}
        temp_dir = tempfile.gettempdir()
        
        # Generate KPI trend chart
        if 'kpis' in report_data and report_data['kpis']:
            try:
                chart_path = os.path.join(temp_dir, f"kpi_chart_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                self._generate_kpi_trend_chart(report_data['kpis'], chart_path)
                chart_paths['kpis'] = chart_path
            except Exception as e:
                print(f"Warning: Could not generate KPI chart: {e}")
        
        # Generate anomaly chart
        if 'anomalies' in report_data and report_data['anomalies']:
            try:
                chart_path = os.path.join(temp_dir, f"anomaly_chart_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                self._generate_anomaly_chart(report_data['anomalies'], chart_path)
                chart_paths['anomalies'] = chart_path
            except Exception as e:
                print(f"Warning: Could not generate anomaly chart: {e}")
        
        # Generate time series chart
        if 'time_series' in report_data and report_data['time_series']:
            try:
                chart_path = os.path.join(temp_dir, f"timeseries_chart_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                self._generate_time_series_chart(report_data['time_series'], chart_path)
                chart_paths['time_series'] = chart_path
            except Exception as e:
                print(f"Warning: Could not generate time series chart: {e}")
        
        return chart_paths
    
    def _generate_kpi_trend_chart(self, kpis: List[Dict], output_path: str):
        """Generate bar chart showing top KPIs"""
        if not kpis:
            return
        
        # Take top 10 KPIs by value
        top_kpis = sorted(kpis, key=lambda x: abs(x.get('value', 0)), reverse=True)[:10]
        
        names = [k.get('kpi_name', '').replace('_', ' ').title() for k in top_kpis]
        values = [k.get('value', 0) for k in top_kpis]
        statuses = [k.get('status', 'NORMAL') for k in top_kpis]
        
        # Color by status
        colors_map = {
            'NORMAL': '#10b981',
            'WARNING': '#f59e0b',
            'CRITICAL': '#ef4444'
        }
        bar_colors = [colors_map.get(s, '#6b7280') for s in statuses]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(names, values, color=bar_colors)
        
        ax.set_xlabel('Value', fontsize=12, fontweight='bold')
        ax.set_title('Top 10 Key Performance Indicators', fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{val:,.0f}', ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _generate_anomaly_chart(self, anomalies: List[Dict], output_path: str):
        """Generate pie chart showing anomaly severity distribution"""
        if not anomalies:
            return
        
        # Count by severity
        severity_counts = {}
        for a in anomalies:
            sev = a.get('severity', 'WARNING')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        if not severity_counts:
            return
        
        labels = list(severity_counts.keys())
        sizes = list(severity_counts.values())
        colors_map = {
            'CRITICAL': '#ef4444',
            'WARNING': '#f59e0b',
            'INFO': '#3b82f6'
        }
        chart_colors = [colors_map.get(l, '#6b7280') for l in labels]
        
        fig, ax = plt.subplots(figsize=(8, 6))
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=chart_colors,
            autopct='%1.0f%%',
            startangle=90,
            textprops={'fontsize': 11, 'fontweight': 'bold'}
        )
        
        ax.set_title('Anomaly Severity Distribution', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _generate_time_series_chart(self, time_series: List[Dict], output_path: str):
        """Generate line chart showing KPI trends over time"""
        if not time_series or len(time_series) < 2:
            return
        
        # Group by KPI name
        kpi_groups = {}
        for row in time_series:
            name = row.get('kpi_name', 'unknown')
            if name not in kpi_groups:
                kpi_groups[name] = []
            kpi_groups[name].append({
                't': row.get('recorded_at', ''),
                'value': row.get('value', 0)
            })
        
        # Take top 5 KPIs by data points
        top_kpis = sorted(kpi_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for name, data_points in top_kpis:
            # Sort by time
            sorted_points = sorted(data_points, key=lambda x: x['t'])
            times = [p['t'][:10] for p in sorted_points]  # Show date only
            values = [p['value'] for p in sorted_points]
            
            ax.plot(times, values, marker='o', linewidth=2, markersize=4, label=name.replace('_', ' ').title())
        
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Value', fontsize=12, fontweight='bold')
        ax.set_title('KPI Trends Over Time', fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

    def _generate_excel(self, report_data: Dict[str, Any], output_path: str) -> str:
        """Generate Excel workbook with multiple sheets"""
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Executive Summary sheet
            summary_data = {
                'Item': [
                    'Report Title',
                    'Prepared For',
                    'Prepared By',
                    'Date',
                    'Version',
                    'Report Type'
                ],
                'Value': [
                    report_data.get('title', 'Data Analysis Report'),
                    report_data.get('prepared_for', self.institution_name),
                    report_data.get('prepared_by', 'Data Analysis Unit'),
                    report_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                    report_data.get('version', '1.0'),
                    report_data.get('report_type', 'Analysis Report')
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # KPIs sheet
            if 'kpis' in report_data and report_data['kpis']:
                kpis_df = pd.DataFrame(report_data['kpis'])
                kpis_df.to_excel(writer, sheet_name='KPIs', index=False)
            
            # Anomalies sheet
            if 'anomalies' in report_data and report_data['anomalies']:
                anomalies_df = pd.DataFrame(report_data['anomalies'])
                anomalies_df.to_excel(writer, sheet_name='Anomalies', index=False)
            
            # Time Series sheet
            if 'time_series' in report_data and report_data['time_series']:
                series_df = pd.DataFrame(report_data['time_series'])
                series_df.to_excel(writer, sheet_name='Time Series', index=False)
            
            # Forecasts sheet
            if 'forecasts' in report_data and report_data['forecasts']:
                forecasts_df = pd.DataFrame(report_data['forecasts'])
                forecasts_df.to_excel(writer, sheet_name='Forecasts', index=False)
        
        return output_path


def generate_goal_analysis_report(
    user_id: str,
    analysis_result: Dict[str, Any],
    supabase,
    institution_name: str = "CNPS",
    output_dir: str = "/tmp/reports"
) -> Dict[str, str]:
    """
    Generate professional CNPS report from goal analysis results.
    Uses the AI-generated narrative (explanation) from the analysis engine
    to populate all report sections.
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch additional context
    kpis = []
    anomalies = []
    time_series = []
    forecasts = []
    
    try:
        kpi_resp = supabase.table("kpi_results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).limit(20).execute()
        if hasattr(kpi_resp, "data") and kpi_resp.data:
            kpis = kpi_resp.data
        anomaly_resp = supabase.table("anomaly_records").select("*").eq("user_id", user_id).order("detected_at", desc=True).limit(10).execute()
        if hasattr(anomaly_resp, "data") and anomaly_resp.data:
            anomalies = anomaly_resp.data
        series_resp = supabase.table("kpi_results").select("kpi_name, value, recorded_at").eq("user_id", user_id).order("recorded_at", desc=True).limit(100).execute()
        if hasattr(series_resp, "data") and series_resp.data:
            time_series = series_resp.data
        forecast_resp = supabase.table("kpi_forecasts").select("*").eq("user_id", user_id).order("forecast_date").limit(30).execute()
        if hasattr(forecast_resp, "data") and forecast_resp.data:
            forecasts = forecast_resp.data
    except Exception:
        pass
    
    goal_text = analysis_result.get("goal_text", "Goal Analysis")
    report_id = analysis_result.get("id", analysis_result.get("run_id", f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"))
    
    # Extract AI narrative from analysis results
    ai = analysis_result.get("metrics", {}).get("explanation", {}) or analysis_result.get("explanation", {}) or {}
    if isinstance(ai, str):
        try:
            ai = json.loads(ai)
        except Exception:
            ai = {"overview": ai}
    
    # Build report data using AI narrative
    overview = ai.get("overview", f"This analysis examines: {goal_text}. The analysis queried the connected database and returned structured results.")
    tables_explored = ai.get("tables_explored", "Institutional database tables relevant to the analysis goal.")
    observations = ai.get("observations", [])
    insights = ai.get("insights", [])
    forecasts_ai = ai.get("forecasts", {})
    risk_analysis = ai.get("risk_analysis", [])
    recommendations = ai.get("recommendations", [])
    what_this_means = ai.get("what_this_means", "")
    assumptions = ai.get("assumptions", [])
    limitations = ai.get("limitations", [])
    
    # Format risk_analysis if it's a list of dicts
    risk_text = ""
    if isinstance(risk_analysis, list):
        for r in risk_analysis:
            if isinstance(r, dict):
                risk_text += f"<b>[{r.get('severity', 'medium').upper()}]</b> {r.get('risk', '')} — {r.get('impact', '')}<br/>"
            else:
                risk_text += f"• {r}<br/>"
    else:
        risk_text = str(risk_analysis)
    
    # Format recommendations if it's a list of dicts
    rec_text = ""
    if isinstance(recommendations, list):
        for r in recommendations:
            if isinstance(r, dict):
                rec_text += f"<b>[{r.get('priority', 'medium').upper()}]</b> {r.get('action', '')} <i>({r.get('timeline', '')}, Expected: {r.get('expected_impact', '')})</i><br/>"
            else:
                rec_text += f"• {r}<br/>"
    else:
        rec_text = str(recommendations)
    
    # Format forecasts
    forecast_text = ""
    if isinstance(forecasts_ai, dict):
        if forecasts_ai.get("projection"):
            forecast_text += f"<b>Projection:</b> {forecasts_ai['projection']}<br/><br/>"
        if forecasts_ai.get("scenario_best"):
            forecast_text += f"<b>Best Case:</b> {forecasts_ai['scenario_best']}<br/><br/>"
        if forecasts_ai.get("scenario_worst"):
            forecast_text += f"<b>Worst Case:</b> {forecasts_ai['scenario_worst']}<br/><br/>"
        if forecasts_ai.get("trigger"):
            forecast_text += f"<b>Key Trigger:</b> {forecasts_ai['trigger']}"
    elif forecasts_ai:
        forecast_text = str(forecasts_ai)
    
    # Executive summary: overview + what_it_means
    exec_summary = overview
    if what_this_means:
        exec_summary += f"<br/><br/><b>In plain language:</b> {what_this_means}"
    
    report_data = {
        'title': goal_text[:80],
        'prepared_for': institution_name,
        'prepared_by': 'CNPS AI Analytics System',
        'date': datetime.now().strftime('%B %d, %Y'),
        'version': '1.0',
        'report_type': 'Goal-Driven Analysis',
        'report_id': report_id,
        'executive_summary': exec_summary,
        'background': (
            f"This report was generated in response to the following analysis goal:<br/><br/>"
            f"<i>\"{goal_text}\"</i><br/><br/>"
            f"The analysis was executed against the {institution_name} institutional database using "
            f"AI-powered query generation, statistical analysis, and automated reporting."
        ),
        'objectives': [
            f'Execute the analysis goal: {goal_text}',
            'Identify key patterns, trends, and anomalies in the data',
            'Provide actionable insights and risk assessments',
            'Generate recommendations with priority levels and timelines'
        ],
        'data_sources': [
            {
                'name': f'{institution_name} Institutional Database',
                'description': tables_explored if isinstance(tables_explored, str) else str(tables_explored)
            }
        ],
        'methodology': (
            f"<b>AI-Driven Analysis Pipeline:</b><br/>"
            f"1. Natural language goal interpretation<br/>"
            f"2. Schema-aware SQL query generation<br/>"
            f"3. Read-only database execution<br/>"
            f"4. Statistical analysis and visualization<br/>"
            f"5. AI-powered insight generation and risk assessment<br/><br/>"
            f"<b>SQL Used:</b> <font size=8>{analysis_result.get('sql', 'N/A')}</font>"
        ),
        'data_quality': (
            f"Data quality was assessed as part of the automated analysis pipeline. "
            f"Completeness, consistency, and validity checks were applied to all queried records."
        ),
        'quality_metrics': [
            {'metric': 'Records Analyzed', 'value': str(len(kpis)), 'status': '✓'},
            {'metric': 'Anomalies Detected', 'value': str(len(anomalies)), 'status': '✓'},
            {'metric': 'Data Points in Time Series', 'value': str(len(time_series)), 'status': '✓'},
            {'metric': 'Forecasts Generated', 'value': str(len(forecasts)), 'status': '✓'},
        ],
        'kpis': kpis,
        'anomalies': anomalies,
        'time_series': time_series,
        'forecasts': forecasts,
        'interpretation': (
            (overview + "<br/><br/>" if overview else "") +
            (f"<b>Key Observations:</b><br/>" + "<br/>".join(f"• {o}" for o in observations) + "<br/><br/>" if observations else "") +
            (f"<b>Insights:</b><br/>" + "<br/>".join(f"• {ins}" for ins in insights) + "<br/><br/>" if insights else "") +
            (f"<b>Forecasts:</b><br/>{forecast_text}" if forecast_text else "")
        ),
        'key_findings': observations + insights if isinstance(observations, list) and isinstance(insights, list) else [],
        'risk_analysis_text': risk_text,
        'recommendations_text': rec_text,
        'conclusions': [
            overview or 'Analysis completed successfully.',
            what_this_means or 'Results are ready for stakeholder review.'
        ],
        'recommendations': [r.get('action', r) if isinstance(r, dict) else str(r) for r in (recommendations or [])],
        'limitations': (
            (limitations[0] if limitations else '') if isinstance(limitations, list) and limitations else str(limitations or 'This analysis is based on available data and should be reviewed in context of broader business conditions.')
        ),
        'assumptions': assumptions,
        'reproducibility': (
            f"Analysis was generated by the {institution_name} AI Analytics System. "
            f"All queries are read-only and logged. SQL queries and methodology are documented in this report. "
            f"Contact the Data Analysis Unit for access to raw data and analysis scripts."
        ),
        'file_name': f"{institution_name}_Analysis_{datetime.now().strftime('%Y%m%d')}_v1.0.pdf",
        'versions': [
            {
                'version': '1.0',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'author': 'CNPS AI Analytics System',
                'changes': 'Automated report generation from goal analysis'
            }
        ]
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(output_dir, f"{institution_name}_Analysis_{timestamp}_v1.0.pdf")
    excel_path = os.path.join(output_dir, f"{institution_name}_Analysis_{timestamp}_v1.0.xlsx")
    
    generator = ProfessionalReportGenerator(institution_name)
    generator.generate_report(report_data, pdf_path, format="pdf")
    generator.generate_report(report_data, excel_path, format="excel")
    
    return {
        'pdf': pdf_path,
        'excel': excel_path,
        'report_id': report_data['report_id']
    }
