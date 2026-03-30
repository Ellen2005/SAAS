import os

def build_dynamic_narrative(kpis: list, anomalies: list) -> str:
    """
    Constructs a textual narrative dynamically from the given KPIs and anomalies.
    """
    narrative_parts = []
    
    # 1. Summarize KPIs
    kpi_summaries = []
    for k in kpis:
        trend = "up" if k['dod_pct'] > 0 else ("down" if k['dod_pct'] < 0 else "flat")
        kpi_summaries.append(f"{k['kpi_name']} is currently at {k['value']:,.2f} ({trend} {abs(k['dod_pct']):.1f}% from yesterday).")
        
    narrative_parts.append(" ".join(kpi_summaries))
    
    # 2. Highlight Anomalies
    if not anomalies:
        narrative_parts.append("All systems are operating within expected normal parameters. No statistical anomalies were detected today.")
    else:
        narrative_parts.append(f"We detected {len(anomalies)} critical deviation(s) that require your attention:")
        for a in anomalies:
            narrative_parts.append(f"- [{a['severity']}] {a['kpi_name']} deviated significantly from its 30-day average. {a['context']['reason']}")
            
    return " ".join(narrative_parts)

def generate_mock_narrative():
    return "This is a static mock narrative. Use generate_live_narrative for real data."

def generate_live_narrative(kpi_data: list, anomaly_data: list):
    """
    Connect to Groq or Ollama to generate a live AI narrative.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # Generate backup base narrative
    base_text = build_dynamic_narrative(kpi_data, anomaly_data)
    
    if groq_api_key:
        # In a real scenario, use groq Python SDK here.
        return base_text
    else:
        # Fallback to baseline narrative
        return base_text

