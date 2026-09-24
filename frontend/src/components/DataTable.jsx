import React, { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

/**
 * Enterprise DataTable — sortable columns, pagination, horizontal scroll, responsive.
 * @param {object} props
 * @param {Array<{key:string, label:string, sortable?:boolean, align?:'left'|'center'|'right', width?:string, format?:function}>} props.columns
 * @param {Array<object>} props.data
 * @param {number} [props.pageSize=10]
 * @param {boolean} [props.showPagination=true]
 * @param {boolean} [props.striped=true]
 * @param {function} [props.onRowClick]
 * @param {string} [props.emptyMessage="No data available"]
 * @param {boolean} [props.loading=false]
 */
const DataTable = ({
  columns = [],
  data = [],
  pageSize = 10,
  showPagination = true,
  striped = true,
  onRowClick,
  emptyMessage = 'No data available',
  loading = false,
}) => {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal), undefined, { sensitivity: 'base' });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = showPagination ? sorted.slice(page * pageSize, (page + 1) * pageSize) : sorted;

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <ChevronsUpDown size={13} style={{ opacity: 0.3 }} />;
    return sortDir === 'asc' ? <ChevronUp size={13} /> : <ChevronDown size={13} />;
  };

  if (loading) {
    return (
      <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--ea-text-muted)' }}>
          <div style={{ width: 28, height: 28, border: '3px solid var(--ea-border)', borderTopColor: 'var(--ea-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto 12px' }} />
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
      <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', minWidth: columns.length > 5 ? 600 : '100%' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--ea-border)' }}>
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  style={{
                    padding: '12px 14px',
                    textAlign: col.align || 'left',
                    fontWeight: 600,
                    fontSize: '0.75rem',
                    color: 'var(--ea-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    cursor: col.sortable !== false ? 'pointer' : 'default',
                    userSelect: 'none',
                    whiteSpace: 'nowrap',
                    position: 'sticky',
                    top: 0,
                    background: 'var(--ea-bg-card)',
                    zIndex: 1,
                    width: col.width,
                  }}
                >
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {col.label}
                    {col.sortable !== false && <SortIcon col={col.key} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: 40, textAlign: 'center', color: 'var(--ea-text-muted)' }}>
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paged.map((row, i) => (
                <tr
                  key={row.id || i}
                  onClick={() => onRowClick?.(row)}
                  style={{
                    borderBottom: i < paged.length - 1 ? '1px solid var(--ea-border)' : 'none',
                    background: striped && i % 2 === 1 ? 'rgba(255,255,255,0.02)' : 'transparent',
                    cursor: onRowClick ? 'pointer' : 'default',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--ea-bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = striped && i % 2 === 1 ? 'rgba(255,255,255,0.02)' : 'transparent'}
                >
                  {columns.map(col => (
                    <td key={col.key} style={{
                      padding: '11px 14px',
                      textAlign: col.align || 'left',
                      color: 'var(--ea-text-primary)',
                      whiteSpace: 'nowrap',
                    }}>
                      {col.format ? col.format(row[col.key], row) : (row[col.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {showPagination && totalPages > 1 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 14px', borderTop: '1px solid var(--ea-border)',
          fontSize: '0.8rem', color: 'var(--ea-text-muted)',
        }}>
          <span>{sorted.length} record{sorted.length !== 1 ? 's' : ''}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <PageBtn onClick={() => setPage(0)} disabled={page === 0}><ChevronsLeft size={14} /></PageBtn>
            <PageBtn onClick={() => setPage(p => p - 1)} disabled={page === 0}><ChevronLeft size={14} /></PageBtn>
            <span style={{ padding: '0 10px', fontWeight: 600, color: 'var(--ea-text-primary)' }}>
              {page + 1} / {totalPages}
            </span>
            <PageBtn onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}><ChevronRight size={14} /></PageBtn>
            <PageBtn onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1}><ChevronsRight size={14} /></PageBtn>
          </div>
        </div>
      )}
    </div>
  );
};

function PageBtn({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: 'none', border: '1px solid var(--ea-border)', borderRadius: 6,
        padding: '4px 8px', color: disabled ? 'var(--ea-text-muted)' : 'var(--ea-text-primary)',
        cursor: disabled ? 'default' : 'pointer', display: 'flex', alignItems: 'center',
        opacity: disabled ? 0.4 : 1, transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  );
}

export default DataTable;
