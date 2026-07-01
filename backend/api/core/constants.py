"""
Shared Constants
================
Centralized constants used across the application.
Eliminates duplicate definitions.
"""

# Legacy demo KPI names that should be hidden from dashboards
LEGACY_DEMO_KPI_NAMES = frozenset({
    "net_revenue", "inventory_value", "support_tickets",
    "Total Revenue", "Inventory Value", "Support Tickets",
})


def is_legacy_demo_kpi(row: dict) -> bool:
    """Check if a row contains a legacy demo KPI name."""
    name = row.get("kpi_name")
    return name in LEGACY_DEMO_KPI_NAMES or (
        name and name.replace("_", " ").title() in LEGACY_DEMO_KPI_NAMES
    )


def is_legacy_demo_report(row: dict) -> bool:
    """Check if a row contains a legacy demo report."""
    narrative = row.get("narrative") or ""
    demo_markers = ("Net Revenue is 190,000", "Inventory Value is", "Support Tickets is 150")
    return all(marker in narrative for marker in demo_markers)
