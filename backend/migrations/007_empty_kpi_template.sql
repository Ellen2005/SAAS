-- Empty default KPI template: admin defines metrics in Semantic Layer.
-- Auto-discovery runs when no admin KPI fields exist.

DELETE FROM public.field_mappings
WHERE template_field_id IN (
  SELECT id FROM public.semantic_fields
  WHERE template_id IN (
    SELECT id FROM public.semantic_templates WHERE name IN ('Standard Analytics KPIs', 'Custom KPIs (admin-defined)')
  )
);

DELETE FROM public.semantic_fields
WHERE template_id IN (
  SELECT id FROM public.semantic_templates WHERE name IN ('Standard Analytics KPIs', 'Custom KPIs (admin-defined)')
);

UPDATE public.semantic_templates
SET
  name = 'Custom KPIs (admin-defined)',
  description = 'Add KPI fields here (Admin → Semantic Layer). Leave empty to auto-discover metrics from the connected database.',
  industry = 'general'
WHERE name = 'Standard Analytics KPIs';

INSERT INTO public.semantic_templates (name, description, industry)
SELECT
  'Custom KPIs (admin-defined)',
  'Add KPI fields here (Admin → Semantic Layer). Leave empty to auto-discover metrics from the connected database.',
  'general'
WHERE NOT EXISTS (
  SELECT 1 FROM public.semantic_templates WHERE name = 'Custom KPIs (admin-defined)'
);

UPDATE public.departments
SET template_id = (SELECT id FROM public.semantic_templates WHERE name = 'Custom KPIs (admin-defined)' LIMIT 1)
WHERE name = 'General' AND template_id IS NULL;
