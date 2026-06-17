"""
Executive AI Briefing Service
=============================
Generates institutional-grade PDF reports for:
  - Monthly DG Report (Rapport Mensuel du Directeur Général)
  - Board Report (Rapport du Conseil d'Administration)
  - Regional Performance Report (Rapport de Performance Régionale)

These are the reports CNPS leadership needs to see — not another dashboard.
"""

import os
import io
import base64
import logging
from datetime import datetime, timezone, date as date_type
from typing import Optional

logger = logging.getLogger(__name__)

# ─── HTML Template for Executive Reports ─────────────────────────────────────

EXECUTIVE_REPORT_CSS = """
<style>
    @page { margin: 20mm 15mm; }
    body { font-family: 'Calibri', 'Arial', sans-serif; color: #1a1a2e; margin: 0; padding: 0; }
    .header { 
        border-bottom: 3px solid #1a3a5c; 
        padding-bottom: 15px; 
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header .title-block h1 { 
        font-size: 22px; color: #1a3a5c; margin: 0; font-weight: 700; 
    }
    .header .title-block h2 { 
        font-size: 14px; color: #4a5568; margin: 4px 0 0 0; font-weight: 400; 
    }
    .header .logo { 
        text-align: right; font-size: 12px; color: #718096; 
    }
    .classification { 
        background: #e53e3e; color: white; padding: 4px 12px; 
        font-size: 10px; font-weight: 700; letter-spacing: 1px;
        display: inline-block; margin-bottom: 15px;
    }
    .meta { 
        display: flex; gap: 30px; margin-bottom: 25px; 
        font-size: 12px; color: #4a5568; 
    }
    .meta span { font-weight: 600; color: #1a3a5c; }
    .executive-summary { 
        background: #f0f4f8; border-left: 4px solid #1a3a5c; 
        padding: 16px 20px; margin-bottom: 25px; border-radius: 0 6px 6px 0;
    }
    .executive-summary h3 { 
        font-size: 14px; color: #1a3a5c; margin: 0 0 8px 0; 
    }
    .executive-summary p { 
        font-size: 12px; line-height: 1.6; margin: 0; 
    }
    .section { margin-bottom: 28px; }
    .section h3 { 
        font-size: 16px; color: #1a3a5c; border-bottom: 1px solid #e2e8f0; 
        padding-bottom: 6px; margin-bottom: 12px; 
    }
    .kpi-grid { 
        display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; 
    }
    .kpi-card { 
        border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 14px; 
    }
    .kpi-card .label { 
        font-size: 11px; color: #718096; margin-bottom: 4px; 
    }
    .kpi-card .value { 
        font-size: 20px; font-weight: 700; color: #1a3a5c; 
    }
    .kpi-card .change { 
        font-size: 11px; margin-top: 2px; 
    }
    .kpi-card .change.positive { color: #38a169; }
    .kpi-card .change.negative { color: #e53e3e; }
    .rag-indicator { 
        display: inline-block; width: 12px; height: 12px; 
        border-radius: 50%; margin-right: 4px; vertical-align: middle; 
    }
    .rag-green { background: #38a169; }
    .rag-amber { background: #d69e2e; }
    .rag-red { background: #e53e3e; }
    table.data { 
        width: 100%; border-collapse: collapse; font-size: 11px; margin: 10px 0; 
    }
    table.data th { 
        background: #1a3a5c; color: white; padding: 8px 10px; text-align: left; font-weight: 600; 
    }
    table.data td { 
        padding: 7px 10px; border-bottom: 1px solid #e2e8f0; 
    }
    table.data tr:nth-child(even) { background: #f7fafc; }
    .recommendation { 
        background: #ebf8ff; border-left: 4px solid #3182ce; 
        padding: 12px 16px; margin-bottom: 10px; border-radius: 0 4px 4px 0;
    }
    .recommendation h4 { margin: 0 0 4px 0; font-size: 13px; color: #2b6cb0; }
    .recommendation p { margin: 0; font-size: 11px; color: #2d3748; }
    .risk-flag { 
        background: #fff5f5; border: 1px solid #fc8181; 
        padding: 10px 14px; margin-bottom: 10px; border-radius: 4px;
    }
    .risk-flag h4 { margin: 0 0 4px 0; font-size: 13px; color: #c53030; }
    .risk-flag p { margin: 0; font-size: 11px; }
    .footer { 
        margin-top: 35px; padding-top: 12px; border-top: 1px solid #e2e8f0; 
        font-size: 10px; color: #a0aec0; text-align: center; 
    }
    .page-break { page-break-before: always; }
    .badge { 
        display: inline-block; padding: 2px 8px; border-radius: 10px; 
        font-size: 10px; font-weight: 600;
    }
    .badge-green { background: #c6f6d5; color: #22543d; }
    .badge-amber { background: #fefcbf; color: #744210; }
    .badge-red { background: #fed7d7; color: #822727; }
    .chart-container { width: 100%; height: 250px; background: #f9f9f9; border-radius: 6px; margin: 10px 0; display: flex; align-items: center; justify-content: center; }
    .chart-placeholder { color: #a0aec0; font-size: 12px; }
</style>
"""


def _rag_status(value: float, thresholds: tuple = (80, 95)) -> str:
    """Return 'green', 'amber', or 'red' based on performance thresholds."""
    if value >= thresholds[1]:
        return 'green'
    elif value >= thresholds[0]:
        return 'amber'
    return 'red'


def _rag_badge(status: str) -> str:
    badge_map = {
        'green': '<span class="rag-indicator rag-green"></span> On Track',
        'amber': '<span class="rag-indicator rag-amber"></span> Needs Attention',
        'red': '<span class="rag-indicator rag-red"></span> Critical',
    }
    return badge_map.get(status, status)


def _format_currency(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} Mrd FCFA"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} M FCFA"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f} K FCFA"
    return f"{value:,.0f} FCFA"


def _kpi_card_html(name: str, value: float, change_pct: float = None, 
                   status: str = "NORMAL", thresholds: tuple = None) -> str:
    change_html = ""
    if change_pct is not None:
        cls = "positive" if change_pct >= 0 else "negative"
        icon = "↑" if change_pct >= 0 else "↓"
        change_html = f'<div class="change {cls}">{icon} {abs(change_pct):.1f}% vs last period</div>'
    
    rag = _rag_status(value, thresholds) if thresholds else 'green'
    
    return f"""
    <div class="kpi-card">
        <div class="label">{name}</div>
        <div class="value">{_format_currency(value)}</div>
        {change_html}
        <div style="margin-top:4px;"><span class="badge badge-{rag.lower() if rag in ['green','amber','red'] else 'green'}">{_rag_badge(rag)}</span></div>
    </div>
    """


def _recommendation_html(title: str, body: str) -> str:
    return f"""
    <div class="recommendation">
        <h4>📋 {title}</h4>
        <p>{body}</p>
    </div>
    """


def _risk_html(title: str, body: str) -> str:
    return f"""
    <div class="risk-flag">
        <h4>⚠️ {title}</h4>
        <p>{body}</p>
    </div>
    """


def _table_html(headers: list, rows: list) -> str:
    header_row = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f"""
    <table class="data">
        <thead><tr>{header_row}</tr></thead>
        <tbody>{body_rows}</tbody>
    </table>
    """


# ─── Report Generators ───────────────────────────────────────────────────────

def generate_dg_report(
    company_name: str = "CNPS",
    report_period: str = None,
    logo_base64: str = "",
    kpis: list = None,
    anomalies: list = None,
    regional_data: list = None,
    department_performance: list = None,
    recommendations: list = None,
    risks: list = None,
    executive_summary: str = "",
) -> str:
    """
    Generate the Director General Monthly Report.
    
    This is the most important report — the DG reads this first thing each month.
    """
    if report_period is None:
        report_period = datetime.now().strftime("%B %Y")
    
    kpis = kpis or []
    anomalies = anomalies or []
    regional_data = regional_data or []
    recommendations = recommendations or []
    risks = risks or []
    
    # KPI Grid
    kpi_grid = ""
    for kpi in kpis[:6]:
        kpi_grid += _kpi_card_html(
            kpi.get("name", "KPI"),
            float(kpi.get("value", 0)),
            float(kpi.get("change_pct")) if kpi.get("change_pct") else None,
            kpi.get("status", "NORMAL"),
            kpi.get("thresholds"),
        )
    
    # Anomalies Section
    anomalies_html = ""
    for anomaly in anomalies[:5]:
        sev = anomaly.get("severity", "WARNING").lower()
        badge_cls = {"critical": "badge-red", "warning": "badge-amber"}.get(sev, "badge-green")
        badge_label = {"critical": "CRITICAL", "warning": "WARNING"}.get(sev, "INFO")
        anomalies_html += f"""
        <tr>
            <td>{anomaly.get('kpi_name', 'N/A')}</td>
            <td><span class="badge {badge_cls}">{badge_label}</span></td>
            <td>{anomaly.get('deviation', 0):.1f}%</td>
            <td>{anomaly.get('context', {}).get('reason', 'N/A')[:120]}</td>
        </tr>"""
    
    if anomalies_html:
        anomalies_html = f"""
        <table class="data">
            <thead><tr><th>KPI</th><th>Severity</th><th>Deviation</th><th>Description</th></tr></thead>
            <tbody>{anomalies_html}</tbody>
        </table>"""
    else:
        anomalies_html = '<p style="color:#38a169;font-weight:600;">✓ No critical anomalies detected this period.</p>'
    
    # Regional Performance Table
    regional_html = ""
    if regional_data:
        regional_html = _table_html(
            ["Region", "Contributions", "Pensions", "AT/MP Claims", "Status"],
            [
                [
                    r.get("name", ""),
                    _format_currency(float(r.get("contributions", 0))),
                    _format_currency(float(r.get("pensions", 0))),
                    str(r.get("claims", 0)),
                    f'<span class="badge badge-{r.get("status", "green")}">{r.get("status", "OK")}</span>'
                ]
                for r in regional_data
            ]
        )
    
    # Recommendations
    recs_html = "".join(
        _recommendation_html(r.get("title", ""), r.get("body", ""))
        for r in recommendations[:3]
    )
    
    # Risks
    risks_html = "".join(
        _risk_html(r.get("title", ""), r.get("body", ""))
        for r in risks[:3]
    )
    
    # Department Performance
    dept_html = ""
    if department_performance:
        dept_html = _table_html(
            ["Department", "KPI Score", "Validation Rate", "Last Sync", "Status"],
            [
                [
                    d.get("name", ""),
                    f'{float(d.get("score", 0)):.1f}%',
                    f'{float(d.get("validation_rate", 0)):.1f}%',
                    d.get("last_sync", "N/A"),
                    f'<span class="badge badge-{d.get("status", "green")}">{d.get("status", "Active")}</span>'
                ]
                for d in department_performance
            ]
        )
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport Mensuel du Directeur Général — {report_period}</title>
{EXECUTIVE_REPORT_CSS}
</head>
<body>

<div class="classification">CONFIDENTIEL — DIRECTION GÉNÉRALE</div>

<div class="header">
    <div class="title-block">
        <h1>Rapport Mensuel du Directeur Général</h1>
        <h2>{company_name} — Période: {report_period}</h2>
    </div>
    <div class="logo">
        <div>Généré le: {datetime.now().strftime("%d/%m/%Y à %H:%M")}</div>
        <div>Classification: Interne</div>
    </div>
</div>

<div class="meta">
    <div><span>Référence:</span> DG-RAP-{datetime.now().strftime("%Y%m")}-001</div>
    <div><span>Période:</span> {report_period}</div>
    <div><span>Statut:</span> <span class="badge badge-green">FINAL</span></div>
</div>

<div class="executive-summary">
    <h3>📊 Synthèse de Direction</h3>
    <p>{executive_summary or "Aucune synthèse générée automatiquement."}</p>
</div>

<!-- KPIs Section -->
<div class="section">
    <h3>Indicateurs Clés de Performance (ICP)</h3>
    <div class="kpi-grid">
        {kpi_grid}
    </div>
</div>

<!-- Anomalies & Risks -->
<div class="section">
    <h3>⚠️ Anomalies et Signaux Faibles</h3>
    {anomalies_html}
    
    {risks_html if risks_html else ""}
</div>

<!-- Regional Performance -->
<div class="section">
    <h3>🏢 Performance Régionale</h3>
    {regional_html if regional_html else "<p>Aucune donnée régionale disponible.</p>"}
</div>

<!-- Department Performance -->
<div class="section page-break">
    <h3>📋 Performance des Directions</h3>
    {dept_html if dept_html else "<p>Aucune donnée directionnelle disponible.</p>"}
</div>

<!-- Recommendations -->
<div class="section">
    <h3>🎯 Recommandations et Actions</h3>
    {recs_html if recs_html else "<p>Aucune recommandation générée.</p>"}
    
    <div style="margin-top:20px; border:1px solid #e2e8f0; border-radius:6px; padding:14px;">
        <h4 style="margin:0 0 8px 0;color:#1a3a5c;">📌 Plan d'Action Prioritaire</h4>
        <ol style="font-size:12px;line-height:1.8;">
            {chr(10).join(f'<li>{r.get("title", "")}</li>' for r in recommendations[:5]) if recommendations else "<li>Aucune action prioritaire identifiée.</li>"}
        </ol>
    </div>
</div>

<div class="footer">
    <p>CNPS — Caisse Nationale de Prévoyance Sociale | Rapport Généré Automatiquement par SAAS Platform</p>
    <p>Ce document est confidentiel. Sa diffusion est strictement réservée à la Direction Générale.</p>
</div>

</body>
</html>"""
    return html


def generate_board_report(
    company_name: str = "CNPS",
    report_period: str = None,
    kpis: list = None,
    strategic_objectives: list = None,
    financial_summary: str = "",
) -> str:
    """
    Generate the Board of Directors Report.
    
    This report focuses on strategic objectives, financial health, and governance.
    """
    if report_period is None:
        report_period = datetime.now().strftime("%B %Y")
    
    kpis = kpis or []
    strategic_objectives = strategic_objectives or []
    
    kpi_grid = ""
    for kpi in kpis[:8]:
        kpi_grid += _kpi_card_html(
            kpi.get("name", "KPI"),
            float(kpi.get("value", 0)),
            float(kpi.get("change_pct")) if kpi.get("change_pct") else None,
            kpi.get("status", "NORMAL"),
        )
    
    # Strategic objectives KPIs
    obj_rows = ""
    for obj in strategic_objectives[:6]:
        progress = float(obj.get("progress", 0))
        rag = _rag_status(progress, (60, 85))
        obj_rows += f"""
        <tr>
            <td>{obj.get("name", "N/A")}</td>
            <td>{obj.get("target", "N/A")}</td>
            <td>{progress:.1f}%</td>
            <td>{obj.get("current", "N/A")}</td>
            <td><span class="badge badge-{rag}">{_rag_badge(rag)}</span></td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport du Conseil d'Administration — {report_period}</title>
{EXECUTIVE_REPORT_CSS}
</head>
<body>

<div class="classification">CONFIDENTIEL — CONSEIL D'ADMINISTRATION</div>

<div class="header">
    <div class="title-block">
        <h1>Rapport du Conseil d'Administration</h1>
        <h2>{company_name} — Exercice {report_period}</h2>
    </div>
    <div class="logo">
        <div>Généré le: {datetime.now().strftime("%d/%m/%Y")}</div>
        <div>Réf: CA-RAP-{datetime.now().strftime("%Y%m")}</div>
    </div>
</div>

<div class="executive-summary">
    <h3>📊 Résumé de Direction</h3>
    <p>{financial_summary or "Présentation de la situation financière et des objectifs stratégiques."}</p>
</div>

<div class="section">
    <h3>🎯 Indicateurs Stratégiques</h3>
    <div class="kpi-grid">
        {kpi_grid}
    </div>
</div>

<div class="section">
    <h3>📊 Progression des Objectifs Stratégiques</h3>
    {_table_html(
        ["Objectif", "Cible", "Progrès", "Réalisé", "Statut"],
        [row for row in [obj_rows] if row]
    ) if obj_rows else "<p>Aucun objectif stratégique défini.</p>"}
</div>

<div class="footer">
    <p>CNPS — Conseil d'Administration | Rapport Généré par SAAS Platform</p>
    <p>Document confidentiel réservé aux membres du Conseil d'Administration.</p>
</div>

</body>
</html>"""
    return html


def generate_regional_performance_report(
    company_name: str = "CNPS",
    report_period: str = None,
    regions: list = None,
) -> str:
    """
    Generate the Regional Performance Report.
    
    Compares all 10 CNPS regional offices on key metrics.
    """
    if report_period is None:
        report_period = datetime.now().strftime("%B %Y")
    
    regions = regions or []
    
    regional_rows = ""
    for region in regions:
        status = region.get("status", "green")
        regional_rows += f"""
        <tr>
            <td><strong>{region.get("name", "N/A")}</strong></td>
            <td>{_format_currency(float(region.get("contributions", 0)))}</td>
            <td>{_format_currency(float(region.get("pensions", 0)))}</td>
            <td>{region.get("claims", 0)}</td>
            <td>{float(region.get("collection_rate", 0)):.1f}%</td>
            <td>{float(region.get("compliance_rate", 0)):.1f}%</td>
            <td><span class="badge badge-{status}">{status.upper()}</span></td>
        </tr>"""
    
    # Leaderboard (top 3 regions)
    sorted_regions = sorted(regions, key=lambda r: float(r.get("collection_rate", 0)), reverse=True)
    leaderboard = ""
    for i, r in enumerate(sorted_regions[:3], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
        leaderboard += f"<tr><td>{medal} {r.get('name', '')}</td><td>{float(r.get('collection_rate', 0)):.1f}%</td><td>{_format_currency(float(r.get('contributions', 0)))}</td></tr>"
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport de Performance Régionale — {report_period}</title>
{EXECUTIVE_REPORT_CSS}
</head>
<body>

<div class="header">
    <div class="title-block">
        <h1>Rapport de Performance Régionale</h1>
        <h2>{company_name} — {report_period}</h2>
    </div>
    <div class="logo">
        <div>Généré le: {datetime.now().strftime("%d/%m/%Y")}</div>
    </div>
</div>

<div class="section">
    <h3>🏆 Classement des Régions</h3>
    {_table_html(["Région", "Taux de Recouvrement", "Cotisations"], 
                 [row for row in [leaderboard] if row]) if leaderboard else "<p>Aucune donnée régionale.</p>"}
</div>

<div class="section">
    <h3>📊 Comparatif Régional Détaillé</h3>
    {_table_html(
        ["Région", "Cotisations", "Pensions", "AT/MP", "Taux Recouvrement", "Taux Conformité", "Statut"],
        [row for row in [regional_rows] if row]
    ) if regional_rows else "<p>Aucune donnée régionale disponible.</p>"}
</div>

<div class="footer">
    <p>CNPS — Direction des Statistiques | Rapport Généré par SAAS Platform</p>
</div>

</body>
</html>"""
    return html


# ─── PDF Rendering ────────────────────────────────────────────────────────────

def render_html_to_pdf(html_content: str) -> bytes:
    """
    Convert HTML report to PDF bytes.
    
    Uses weasyprint if available, otherwise returns HTML as bytes
    (browsers can save-as-PDF via print dialog).
    """
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        logger.info(f"PDF generated successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes
    except ImportError:
        logger.warning("weasyprint not installed. Returning HTML for browser print-to-PDF.")
        return html_content.encode("utf-8")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}. Falling back to HTML.")
        return html_content.encode("utf-8")


def generate_pdf_report(
    report_type: str,
    company_name: str = "CNPS",
    report_period: str = None,
    **kwargs,
) -> tuple:
    """
    Generate a complete PDF report.
    
    Args:
        report_type: "dg", "board", or "regional"
        company_name: Institution name
        report_period: Period string (e.g. "June 2026")
        **kwargs: Additional data passed to the specific generator
    
    Returns:
        Tuple of (pdf_bytes, filename, html_content)
    """
    generators = {
        "dg": generate_dg_report,
        "board": generate_board_report,
        "regional": generate_regional_performance_report,
    }
    
    generator = generators.get(report_type)
    if not generator:
        raise ValueError(f"Unknown report type: {report_type}. Use 'dg', 'board', or 'regional'.")
    
    html = generator(
        company_name=company_name,
        report_period=report_period,
        **kwargs,
    )
    
    period_slug = (report_period or datetime.now().strftime("%Y-%m")).replace(" ", "_").lower()
    filenames = {
        "dg": f"Rapport_DG_{period_slug}",
        "board": f"Rapport_CA_{period_slug}",
        "regional": f"Performance_Regionale_{period_slug}",
    }
    filename = filenames.get(report_type, f"Rapport_{period_slug}")
    
    pdf_bytes = render_html_to_pdf(html)
    
    return pdf_bytes, f"{filename}.pdf", html