-- =============================================================================
-- CNPS KPI definitions + semantic template seed
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.kpi_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    display_name_en VARCHAR(200) NOT NULL,
    display_name_fr VARCHAR(200),
    formula_hint TEXT,
    unit VARCHAR(50),
    domain VARCHAR(80),
    widget_type VARCHAR(40) DEFAULT 'stat',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO public.kpi_definitions (name, display_name_en, display_name_fr, formula_hint, unit, domain, widget_type, sort_order)
VALUES
    ('contribution_collection_rate', 'Contribution Collection Rate', 'Taux de recouvrement des cotisations', 'paid contributions / expected', 'percent', 'contribution', 'stat', 1),
    ('total_contributions', 'Total Contributions', 'Total des cotisations', 'SUM(contribution_amount)', 'currency', 'contribution', 'area', 2),
    ('pension_disbursement', 'Monthly Pension Disbursement', 'Versements mensuels des pensions', 'SUM(pension_amount) by month', 'currency', 'pension', 'area', 3),
    ('active_employers', 'Active Employers', 'Employeurs actifs', 'COUNT active employers', 'count', 'employer', 'stat', 4),
    ('workplace_accident_frequency', 'Workplace Accident Frequency', 'Fréquence des accidents du travail', 'COUNT accidents per period', 'count', 'claim', 'line', 5),
    ('delinquent_employers', 'Delinquent Employers', 'Employeurs en retard', 'employers with overdue contributions', 'count', 'compliance', 'stat', 6),
    ('regional_contribution_share', 'Regional Contribution Share', 'Part régionale des cotisations', '% by regional_code', 'percent', 'regional', 'bar', 7),
    ('contribution_arrears', 'Contribution Arrears', 'Arriérés de cotisations', 'SUM overdue amounts', 'currency', 'contribution', 'stat', 8)
ON CONFLICT (name) DO NOTHING;

-- CNPS semantic template
INSERT INTO public.semantic_templates (id, name, description)
SELECT gen_random_uuid(), 'CNPS Core Schema', 'Standard institutional schema for CNPS contributions, pensions, and workplace accidents'
WHERE NOT EXISTS (SELECT 1 FROM public.semantic_templates WHERE name = 'CNPS Core Schema');

INSERT INTO public.semantic_fields (template_id, global_field_name, data_type, required, description)
SELECT t.id, f.global_field_name, f.data_type, f.required, f.description
FROM public.semantic_templates t
CROSS JOIN (
    VALUES
        ('contribution_amount', 'currency', true, 'Cotisation amount'),
        ('contribution_date', 'date', true, 'Date of contribution'),
        ('employee_id', 'string', true, 'Insured worker identifier'),
        ('employer_id', 'string', true, 'Employer identifier'),
        ('payment_status', 'string', true, 'paid, pending, overdue'),
        ('pension_amount', 'currency', false, 'Pension payment amount'),
        ('regional_code', 'string', false, 'Regional office code'),
        ('accident_date', 'date', false, 'Workplace accident date'),
        ('claim_status', 'string', false, 'AT/MP claim status')
) AS f(global_field_name, data_type, required, description)
WHERE t.name = 'CNPS Core Schema'
  AND NOT EXISTS (
      SELECT 1 FROM public.semantic_fields sf
      WHERE sf.template_id = t.id AND sf.global_field_name = f.global_field_name
  );
