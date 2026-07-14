import React, { useMemo } from 'react';

function parseNarrative(text) {
  if (!text) return [];

  const lines = text.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Detect markdown table (line with | characters)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableRows = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const row = lines[i].trim();
        // Skip separator rows like |---|---|
        if (/^\|[\s\-:|]+\|$/.test(row)) {
          i++;
          continue;
        }
        const cells = row.split('|').slice(1, -1).map(c => c.trim());
        tableRows.push(cells);
        i++;
      }
      if (tableRows.length > 0) {
        elements.push({ type: 'table', rows: tableRows });
      }
      continue;
    }

    // Detect section headers (bold text lines or lines ending with colon)
    if (/^#{1,3}\s/.test(line)) {
      elements.push({ type: 'heading', text: line.replace(/^#{1,3}\s*/, '') });
      i++;
      continue;
    }

    // Detect bold headers like "**KPI Analysis**" or lines that look like section titles
    if (/^\*\*[^*]+\*\*\s*$/.test(line.trim())) {
      elements.push({ type: 'heading', text: line.replace(/\*\*/g, '').trim() });
      i++;
      continue;
    }

    // Detect lines like "KPI Analysis" or "Anomalies" (single-line section titles followed by a blank line or content)
    if (line.trim() && !line.trim().startsWith('-') && !line.trim().startsWith('*') &&
        i + 1 < lines.length && (lines[i + 1].trim() === '' || /^[A-Z]/.test(lines[i + 1].trim())) &&
        line.trim().length < 60 && /^[A-Z]/.test(line.trim()) &&
        !line.includes('.') && !line.includes(',') &&
        (i === 0 || lines[i - 1].trim() === '')) {
      elements.push({ type: 'heading', text: line.trim() });
      i++;
      continue;
    }

    // Regular paragraph text
    if (line.trim()) {
      elements.push({ type: 'paragraph', text: line.trim() });
    }
    i++;
  }

  return elements;
}

function renderInlineFormatting(text) {
  // Handle bold, italic, and code
  const parts = [];
  let remaining = text;
  let key = 0;

  while (remaining) {
    // Bold
    let match = remaining.match(/\*\*(.+?)\*\*/);
    if (match) {
      const idx = remaining.indexOf(match[0]);
      if (idx > 0) parts.push(<span key={key++}>{remaining.slice(0, idx)}</span>);
      parts.push(<strong key={key++} style={{ color: 'var(--ea-text-primary)' }}>{match[1]}</strong>);
      remaining = remaining.slice(idx + match[0].length);
      continue;
    }

    // Italic
    match = remaining.match(/\*(.+?)\*/);
    if (match) {
      const idx = remaining.indexOf(match[0]);
      if (idx > 0) parts.push(<span key={key++}>{remaining.slice(0, idx)}</span>);
      parts.push(<em key={key++}>{match[1]}</em>);
      remaining = remaining.slice(idx + match[0].length);
      continue;
    }

    parts.push(<span key={key++}>{remaining}</span>);
    break;
  }

  return parts;
}

export default function NarrativeRenderer({ text, style = {} }) {
  const elements = useMemo(() => parseNarrative(text), [text]);

  if (!text) return null;

  return (
    <div className="narrative-content" style={{ fontSize: '0.95rem', lineHeight: 1.75, ...style }}>
      {elements.map((el, i) => {
        if (el.type === 'heading') {
          return (
            <h4 key={i} style={{
              fontSize: '1.05rem',
              fontWeight: 700,
              color: 'var(--ea-text-primary)',
              marginTop: i > 0 ? 20 : 0,
              marginBottom: 8,
              borderBottom: '1px solid var(--ea-border)',
              paddingBottom: 6,
            }}>
              {renderInlineFormatting(el.text)}
            </h4>
          );
        }

        if (el.type === 'table') {
          return (
            <div key={i} style={{ overflowX: 'auto', margin: '12px 0' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '0.85rem',
              }}>
                <thead>
                  <tr>
                    {el.rows[0]?.map((cell, ci) => (
                      <th key={ci} style={{
                        textAlign: 'left',
                        padding: '8px 12px',
                        borderBottom: '2px solid var(--ea-primary)',
                        color: 'var(--ea-text-primary)',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                        background: 'rgba(79, 70, 229, 0.05)',
                      }}>
                        {renderInlineFormatting(cell)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {el.rows.slice(1).map((row, ri) => (
                    <tr key={ri} style={{
                      background: ri % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                    }}>
                      {row.map((cell, ci) => (
                        <td key={ci} style={{
                          padding: '7px 12px',
                          borderBottom: '1px solid var(--ea-border)',
                          color: 'var(--ea-text-secondary)',
                          whiteSpace: 'nowrap',
                        }}>
                          {renderInlineFormatting(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        // Paragraph
        return (
          <p key={i} style={{
            marginBottom: 8,
            color: 'var(--ea-text-secondary)',
          }}>
            {renderInlineFormatting(el.text)}
          </p>
        );
      })}
    </div>
  );
}
