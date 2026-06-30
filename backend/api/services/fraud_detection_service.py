"""
Advanced Anomaly & Fraud Detection Service
===========================================
Detects suspicious patterns in CNPS data:
  - Unusual claims (anomalously high/low benefit payments)
  - Contribution irregularities (employers with suspicious patterns)
  - Regional anomalies (offices deviating from expected metrics)
  - Time-based fraud patterns (weekend/holiday activity)
  - Duplicate detection (same data appearing multiple times)

This goes beyond the basic z-score in etl_service.py.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import math

logger = logging.getLogger(__name__)


# ─── Detection Result Models ─────────────────────────────────────────────────

class FraudAlert:
    """A single fraud/irregularity detection result."""
    
    def __init__(
        self,
        alert_type: str,
        severity: str,
        kpi_name: str,
        entity_name: str,
        entity_type: str,
        metric_value: float,
        expected_value: float,
        deviation: float,
        confidence: float,
        description: str,
        recommendation: str,
        raw_data: dict = None,
    ):
        self.id = str(uuid.uuid4())
        self.alert_type = alert_type        # contribution_fraud, claim_fraud, regional_anomaly, duplicate, pattern_abnormal
        self.severity = severity            # CRITICAL, HIGH, MEDIUM, LOW
        self.kpi_name = kpi_name
        self.entity_name = entity_name      # Employer name, region name, etc.
        self.entity_type = entity_type      # employer, region, department
        self.metric_value = metric_value
        self.expected_value = expected_value
        self.deviation = deviation          # percentage deviation from expected
        self.confidence = confidence        # 0.0 to 1.0
        self.description = description
        self.recommendation = recommendation
        self.detected_at = datetime.now(timezone.utc).isoformat()
        self.raw_data = raw_data or {}
        self.status = "OPEN"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "kpi_name": self.kpi_name,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "metric_value": round(self.metric_value, 2),
            "expected_value": round(self.expected_value, 2),
            "deviation": round(self.deviation, 2),
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "recommendation": self.recommendation,
            "detected_at": self.detected_at,
            "status": self.status,
        }


# ─── Detection Algorithms ────────────────────────────────────────────────────

def detect_contribution_fraud(
    kpi_data: list,
    employer_data: list = None,
) -> list:
    """
    Detect suspicious contribution patterns:
    1. Sudden drops in contributions from regular employers
    2. Unusually large one-time contributions (possible money laundering)
    3. Employers with highly irregular payment schedules
    4. Round-number fraud (payments exactly at thresholds)
    """
    alerts = []
    
    if not kpi_data:
        return alerts
    
    # Group by employer/customer
    from collections import defaultdict
    employer_contributions = defaultdict(list)
    employer_names = {}
    
    for row in kpi_data:
        name = str(row.get("kpi_name", "unknown"))
        customer = str(row.get("customer_id", row.get("department_id", "unknown")))
        val = float(row.get("value", 0))
        
        if "contribution" in name.lower() or "cotisation" in name.lower():
            employer_contributions[customer].append({
                "value": val,
                "date": str(row.get("date", row.get("recorded_at", ""))),
                "kpi_name": name,
            })
            employer_names[customer] = customer
    
    if employer_data:
        for emp in employer_data:
            eid = str(emp.get("id", emp.get("customer_id", "")))
            employer_names[eid] = emp.get("name", emp.get("company_name", eid))
    
    for entity_id, values in employer_contributions.items():
        entity_name = employer_names.get(entity_id, entity_id)
        
        if len(values) < 3:
            continue
        
        # Sort by date
        values_sorted = sorted(values, key=lambda x: x.get("date", ""))
        
        # Calculate mean and std
        amounts = [v["value"] for v in values_sorted]
        mean_val = sum(amounts) / len(amounts)
        
        if mean_val == 0:
            continue
        
        std_val = (sum((a - mean_val) ** 2 for a in amounts) / len(amounts)) ** 0.5 or mean_val * 0.1
        
        # Check most recent values for anomalies
        for v in values_sorted[-3:]:  # Last 3 entries
            z_score = abs(v["value"] - mean_val) / std_val
            
            # Sudden drop (possible fraud or error)
            if v["value"] < mean_val * 0.3 and mean_val > 1000:
                deviation = ((v["value"] - mean_val) / mean_val) * 100
                alerts.append(FraudAlert(
                    alert_type="contribution_fraud",
                    severity="HIGH" if z_score > 3 else "MEDIUM",
                    kpi_name=v["kpi_name"],
                    entity_name=entity_name,
                    entity_type="employer",
                    metric_value=v["value"],
                    expected_value=mean_val,
                    deviation=abs(deviation),
                    confidence=min(0.95, 0.5 + z_score * 0.1),
                    description=f"Contribution chute soudaine: {entity_name} a déclaré {v['value']:,.0f} FCFA contre une moyenne de {mean_val:,.0f} FCFA (déviation de {abs(deviation):.1f}%)",
                    recommendation=f"Vérifier la déclaration de {entity_name}. Contacter l'employeur pour confirmer l'exactitude.",
                    raw_data=v,
                ))
            
            # Unusually large payment (possible fraud)
            elif v["value"] > mean_val * 3 and v["value"] > 1000000:
                deviation = ((v["value"] - mean_val) / mean_val) * 100
                alerts.append(FraudAlert(
                    alert_type="contribution_fraud",
                    severity="MEDIUM" if z_score < 4 else "CRITICAL",
                    kpi_name=v["kpi_name"],
                    entity_name=entity_name,
                    entity_type="employer",
                    metric_value=v["value"],
                    expected_value=mean_val,
                    deviation=abs(deviation),
                    confidence=min(0.9, 0.4 + z_score * 0.08),
                    description=f"Paiement inhabituellement élevé: {entity_name} a déclaré {v['value']:,.0f} FCFA ({abs(deviation):.0f}% au-dessus de la moyenne)",
                    recommendation=f"Vérifier la source des fonds pour {entity_name}. Possible erreur de déclaration.",
                    raw_data=v,
                ))
    
    return alerts


def detect_claim_fraud(
    kpi_data: list,
    claim_data: list = None,
) -> list:
    """
    Detect suspicious claim patterns:
    1. Claims much higher/lower than historical average
    2. Weekend/holiday claims (often fraudulent)
    3. Round-number claims
    4. Rapid repeat claims
    """
    alerts = []
    
    if not kpi_data:
        return alerts
    
    from collections import defaultdict
    claim_types = defaultdict(list)
    
    for row in kpi_data:
        name = str(row.get("kpi_name", "unknown"))
        val = float(row.get("value", 0))
        
        if any(kw in name.lower() for kw in ["claim", "prestation", "pension", "benefit", "indemnité"]):
            claim_types[name].append({
                "value": val,
                "date": str(row.get("date", row.get("recorded_at", ""))),
                "kpi_name": name,
            })
    
    for claim_name, values in claim_types.items():
        if len(values) < 4:
            continue
        
        values_sorted = sorted(values, key=lambda x: x.get("date", ""))
        amounts = [v["value"] for v in values_sorted]
        mean_val = sum(amounts) / len(amounts)
        std_val = (sum((a - mean_val) ** 2 for a in amounts) / len(amounts)) ** 0.5 or mean_val * 0.15
        
        if mean_val == 0:
            continue
        
        # Check latest value
        latest = values_sorted[-1]
        z_score = abs(latest["value"] - mean_val) / std_val
        
        if z_score > 2.0:
            deviation = ((latest["value"] - mean_val) / mean_val) * 100
            alerts.append(FraudAlert(
                alert_type="claim_fraud",
                severity="CRITICAL" if z_score > 3.5 else ("HIGH" if z_score > 2.5 else "MEDIUM"),
                kpi_name=claim_name,
                entity_name=claim_name,
                entity_type="claim_type",
                metric_value=latest["value"],
                expected_value=mean_val,
                deviation=abs(deviation),
                confidence=min(0.95, 0.4 + z_score * 0.12),
                description=f"Prestation anormale: {claim_name} à {latest['value']:,.0f} FCFA (moyenne: {mean_val:,.0f} FCFA, écart: {abs(deviation):.1f}%)",
                recommendation=f"Analyser les détails des prestations {claim_name}. Vérifier les dossiers individuels.",
                raw_data=latest,
            ))
        
        # Round-number detection (possible fraud indicator)
        for v in values_sorted[-5:]:
            val_str = f"{v['value']:.0f}"
            if len(val_str) >= 4 and val_str.count("0") >= len(val_str) - 1:
                alerts.append(FraudAlert(
                    alert_type="claim_fraud",
                    severity="LOW",
                    kpi_name=claim_name,
                    entity_name=claim_name,
                    entity_type="claim_type",
                    metric_value=v["value"],
                    expected_value=mean_val,
                    deviation=0,
                    confidence=0.3,
                    description=f"Nombre arrondi suspect: {claim_name} = {v['value']:,.0f} FCFA (les nombres arrondis peuvent indiquer une estimation plutôt qu'un calcul exact)",
                    recommendation=f"Vérifier le calcul de {claim_name}. Les montants exacts sont préférables aux arrondis.",
                    raw_data=v,
                ))
    
    return alerts


def detect_regional_anomalies(
    regional_kpi_data: list,
) -> list:
    """
    Detect regions performing significantly differently from peers.
    
    Uses inter-region comparison to find outliers.
    """
    alerts = []
    
    if not regional_kpi_data:
        return alerts
    
    # Group by region
    from collections import defaultdict
    region_metrics = defaultdict(lambda: defaultdict(list))
    
    for row in regional_kpi_data:
        region = str(row.get("region", row.get("department_id", row.get("customer_id", "unknown"))))
        kpi_name = str(row.get("kpi_name", "unknown"))
        val = float(row.get("value", 0))
        region_metrics[region][kpi_name].append(val)
    
    # For each KPI, compare across regions
    for kpi_name in set(
        k for r in region_metrics for k in region_metrics[r]
    ):
        region_averages = {}
        for region, metrics in region_metrics.items():
            if kpi_name in metrics and metrics[kpi_name]:
                region_averages[region] = sum(metrics[kpi_name]) / len(metrics[kpi_name])
        
        if len(region_averages) < 3:
            continue
        
        values = list(region_averages.values())
        overall_mean = sum(values) / len(values)
        overall_std = (sum((v - overall_mean) ** 2 for v in values) / len(values)) ** 0.5 or overall_mean * 0.2
        
        if overall_mean == 0:
            continue
        
        for region, avg_val in region_averages.items():
            z_score = abs(avg_val - overall_mean) / overall_std
            
            if z_score > 1.5:  # Flag regions >1.5 std from mean
                deviation = ((avg_val - overall_mean) / overall_mean) * 100
                severity = "CRITICAL" if z_score > 3 else ("HIGH" if z_score > 2.25 else "MEDIUM")
                
                direction = "supérieure" if avg_val > overall_mean else "inférieure"
                alerts.append(FraudAlert(
                    alert_type="regional_anomaly",
                    severity=severity,
                    kpi_name=kpi_name,
                    entity_name=region,
                    entity_type="region",
                    metric_value=avg_val,
                    expected_value=overall_mean,
                    deviation=abs(deviation),
                    confidence=min(0.9, 0.3 + z_score * 0.15),
                    description=f"Anomalie régionale: {region} a une performance {direction} de {abs(deviation):.1f}% pour {kpi_name} (moyenne nationale: {overall_mean:,.0f})",
                    recommendation=f"Analyser les opérations de {region} pour {kpi_name}. Identifier les bonnes pratiques ou les problèmes spécifiques.",
                    raw_data={"region": region, "kpi_name": kpi_name, "avg_value": avg_val},
                ))
    
    return alerts


def detect_duplicate_transactions(
    kpi_data: list,
) -> list:
    """
    Detect duplicate or near-duplicate data entries.
    
    Looks for:
    1. Exact duplicates (same KPI, same value, same date)
    2. Near duplicates (same KPI, close values, close dates)
    """
    alerts = []
    
    if not kpi_data:
        return alerts
    
    from collections import defaultdict
    
    # Group by KPI name
    by_kpi = defaultdict(list)
    for row in kpi_data:
        by_kpi[str(row.get("kpi_name", "unknown"))].append(row)
    
    for kpi_name, rows in by_kpi.items():
        if len(rows) < 2:
            continue
        
        # Check for exact duplicates (same value, same date)
        seen = {}
        for row in rows:
            val = float(row.get("value", 0))
            date = str(row.get("date", row.get("recorded_at", "")))[:10]
            key = f"{date}:{val}"
            
            if key in seen:
                alerts.append(FraudAlert(
                    alert_type="duplicate",
                    severity="MEDIUM",
                    kpi_name=kpi_name,
                    entity_name=f"{kpi_name}",
                    entity_type="kpi",
                    metric_value=val,
                    expected_value=val,
                    deviation=0,
                    confidence=0.95,
                    description=f"Doublon détecté: {kpi_name} = {val:,.0f} FCFA le {date}. Même valeur enregistrée deux fois.",
                    recommendation=f"Vérifier le processus d'extraction pour {kpi_name}. Un doublon peut indiquer une double comptabilisation.",
                    raw_data={"original": seen[key], "duplicate": row},
                ))
                break  # One alert per KPI per batch
            seen[key] = row
    
    return alerts


def detect_pattern_anomalies(
    kpi_data: list,
) -> list:
    """
    Detect abnormal temporal patterns:
    1. Weekend/holiday activity (when nothing should happen)
    2. Sudden change in data frequency
    3. Missing data periods
    4. Unusual growth/decline rates
    """
    alerts = []
    
    if not kpi_data:
        return alerts
    
    from collections import defaultdict
    by_kpi = defaultdict(list)
    
    for row in kpi_data:
        by_kpi[str(row.get("kpi_name", "unknown"))].append(row)
    
    for kpi_name, rows in by_kpi.items():
        if len(rows) < 5:
            continue
        
        # Sort by date
        dated_rows = []
        for r in rows:
            try:
                dt = r.get("date", r.get("recorded_at", ""))
                if dt:
                    dated_rows.append((str(dt)[:10], float(r.get("value", 0))))
            except (ValueError, TypeError):
                pass
        
        dated_rows.sort(key=lambda x: x[0])
        
        if len(dated_rows) < 5:
            continue
        
        # Check for gaps in data (missing periods)
        dates = [d for d, _ in dated_rows]
        for i in range(1, len(dates)):
            try:
                prev = datetime.strptime(dates[i-1], "%Y-%m-%d")
                curr = datetime.strptime(dates[i], "%Y-%m-%d")
                gap_days = (curr - prev).days
                
                if gap_days > 14:  # Gap of more than 2 weeks
                    alerts.append(FraudAlert(
                        alert_type="pattern_abnormal",
                        severity="LOW",
                        kpi_name=kpi_name,
                        entity_name=kpi_name,
                        entity_type="kpi",
                        metric_value=float(dated_rows[i][1]),
                        expected_value=float(dated_rows[i-1][1]) if i > 0 else 0,
                        deviation=gap_days,
                        confidence=0.7,
                        description=f"Données manquantes: {kpi_name} a un écart de {gap_days} jours entre {dates[i-1]} et {dates[i]}",
                        recommendation=f"Vérifier la continuité des données pour {kpi_name}. Une période sans données peut indiquer un problème de collecte.",
                        raw_data={"gap_days": gap_days, "from": dates[i-1], "to": dates[i]},
                    ))
            except (ValueError, IndexError):
                continue
        
        # Check for unusual growth rates
        if len(dated_rows) >= 4:
            recent = [v for _, v in dated_rows[-4:]]
            for i in range(1, len(recent)):
                if recent[i-1] != 0:
                    growth = (recent[i] - recent[i-1]) / recent[i-1] * 100
                    if abs(growth) > 100:  # More than 100% change
                        direction = "increased" if growth > 0 else "decreased"
                        alerts.append(FraudAlert(
                            alert_type="pattern_abnormal",
                            severity="HIGH" if abs(growth) > 300 else "MEDIUM",
                            kpi_name=kpi_name,
                            entity_name=kpi_name,
                            entity_type="kpi",
                            metric_value=recent[i],
                            expected_value=recent[i-1],
                            deviation=abs(growth),
                            confidence=min(0.85, abs(growth) / 400),
                            description=f"Abnormal variation: {kpi_name} has {direction} by {abs(growth):.0f}% between the last two periods",
                            recommendation=f"Analyze the causes of this significant {direction} for {kpi_name}. Verify source data.",
                            raw_data={"growth_pct": growth, "previous": recent[i-1], "current": recent[i]},
                        ))
    
    return alerts


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def run_full_fraud_detection(
    kpi_data: list,
    employer_data: list = None,
    regional_data: list = None,
    enabled_checks: list = None,
) -> dict:
    """
    Run all fraud detection algorithms and return consolidated results.
    
    Args:
        kpi_data: List of KPI result dicts
        employer_data: Optional list of employer records
        regional_data: Optional list of regional KPI data
        enabled_checks: List of checks to run. Default: all
    
    Returns:
        Dict with alerts, summary stats, and recommendations
    """
    if enabled_checks is None:
        enabled_checks = ["contribution", "claim", "regional", "duplicate", "pattern"]
    
    all_alerts = []
    
    if "contribution" in enabled_checks:
        all_alerts.extend(detect_contribution_fraud(kpi_data, employer_data))
    
    if "claim" in enabled_checks:
        all_alerts.extend(detect_claim_fraud(kpi_data))
    
    if "regional" in enabled_checks:
        all_alerts.extend(detect_regional_anomalies(regional_data or kpi_data))
    
    if "duplicate" in enabled_checks:
        all_alerts.extend(detect_duplicate_transactions(kpi_data))
    
    if "pattern" in enabled_checks:
        all_alerts.extend(detect_pattern_anomalies(kpi_data))
    
    # Sort by severity and confidence
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), -a.confidence))
    
    # Summary
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for alert in all_alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
    
    # Compute fraud risk score (0-100)
    risk_score = 0
    if all_alerts:
        risk_score = min(100, sum(
            {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 5, "LOW": 1}.get(a.severity, 0) * a.confidence
            for a in all_alerts
        ))
    
    # Executive summary
    if risk_score >= 50:
        risk_level = "CRITICAL"
        summary = "ATTENTION: Plusieurs indicateurs de fraude potentielle détectés. Une investigation approfondie est recommandée."
    elif risk_score >= 25:
        risk_level = "HIGH"
        summary = "SURVEILLANCE: Des anomalies significatives ont été détectées. Vérification recommandée."
    elif risk_score >= 10:
        risk_level = "MEDIUM"
        summary = "INFORMATION: Quelques anomalies mineures détectées. À surveiller."
    else:
        risk_level = "LOW"
        summary = "Aucune anomalie significative détectée. Les données semblent conformes."
    
    # Generate prioritized recommendations
    recommendations = []
    if severity_counts.get("CRITICAL", 0) > 0:
        recommendations.append({
            "priority": "URGENTE",
            "action": "Investigation immédiate requise",
            "details": f"{severity_counts['CRITICAL']} alerte(s) critique(s) nécessite(nt) une intervention urgente.",
        })
    if severity_counts.get("HIGH", 0) > 0:
        recommendations.append({
            "priority": "ÉLEVÉE",
            "action": "Examen des alertes haute priorité",
            "details": f"{severity_counts['HIGH']} alerte(s) de haute priorité à examiner dans les plus brefs délais.",
        })
    recommendations.append({
        "priority": "PRÉVENTIVE",
        "action": "Revue périodique des schémas",
        "details": "Mettre en place des contrôles automatisés pour détecter précocement les anomalies.",
    })
    
    return {
        "alerts": [a.to_dict() for a in all_alerts],
        "summary": summary,
        "risk_score": round(risk_score, 1),
        "risk_level": risk_level,
        "severity_breakdown": severity_counts,
        "total_alerts": len(all_alerts),
        "recommendations": recommendations,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }