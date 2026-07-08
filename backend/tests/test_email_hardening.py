from api.services.email_service import generate_professional_html_email, normalize_recipient_email


def test_generate_professional_html_email_escapes_html_content():
    html = generate_professional_html_email(
        kpis=[{"kpi_name": "Revenue", "value": 100.0, "status": "NORMAL"}],
        narrative_text='<script>alert("x")</script>',
        chart_url="",
        anomalies=[],
        department_name='Sales <b>Team</b>',
        recipient_email="user@example.com",
    )

    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html
    assert "Sales &lt;b&gt;Team&lt;/b&gt;" in html
    assert "<script>" not in html


def test_normalize_recipient_email_rejects_invalid_inputs():
    assert normalize_recipient_email(" user@example.com ") == "user@example.com"
    assert normalize_recipient_email("not-an-email") is None
    assert normalize_recipient_email("") is None
