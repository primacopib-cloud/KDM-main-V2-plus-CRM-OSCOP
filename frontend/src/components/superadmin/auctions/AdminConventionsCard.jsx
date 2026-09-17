import { useEffect, useState } from 'react';
import { FileSpreadsheet, ScrollText } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Archive des conventions cadre POP'S signées (superadmin)
export const AdminConventionsCard = () => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    fetch(`${API}/admin/detaillant/conventions`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { conventions: [] }))
      .then((d) => setItems(d.conventions || [])).catch(() => {});
  }, []);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="admin-conventions-card">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <ScrollText className="w-4 h-4" /> Conventions cadre signées ({items.length})
        </h3>
        <button type="button" onClick={() => {
            const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
            const rows = [['Boutique POP\'S', 'Localité', 'Pays', 'Signataire', 'Signée le', 'Version'].map(esc).join(';')];
            items.forEach((c) => rows.push([c.company_name, c.locality, c.country_code,
              c.signer_name, c.signed_at, c.version].map(esc).join(';')));
            const blob = new Blob(['﻿' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'conventions-pops-signees.csv';
            a.click();
            URL.revokeObjectURL(a.href);
          }} disabled={items.length === 0} data-testid="conventions-export-csv"
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[11px] font-bold bg-[#D9B35A] text-[#2A1045] on-gold disabled:opacity-40">
          <FileSpreadsheet className="w-3.5 h-3.5" /> Export CSV
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-white/40" data-testid="admin-conventions-empty">Aucune convention signée.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-white/45 text-left">
              <th className="pr-2 pb-1">Boutique POP'S</th><th className="pr-2">Localité</th>
              <th className="pr-2">Signataire</th><th className="pr-2">Signée le</th><th>Version</th>
            </tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.user_id} className="border-t border-white/[0.06] text-white/70"
                  data-testid={`convention-row-${c.user_id}`}>
                  <td className="pr-2 py-1.5 font-bold text-white/85">{c.company_name}</td>
                  <td className="pr-2">{c.locality || '—'}{c.country_code ? ` (${c.country_code})` : ''}</td>
                  <td className="pr-2">{c.signer_name}</td>
                  <td className="pr-2">{fmt(c.signed_at)}</td>
                  <td>{c.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
