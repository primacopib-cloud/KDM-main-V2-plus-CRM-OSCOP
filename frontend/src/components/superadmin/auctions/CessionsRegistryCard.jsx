import { useEffect, useState } from 'react';
import { FileSpreadsheet, Search } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';

const STATUSES = [['', 'Toutes'], ['DRAFT', 'À signer'], ['SIGNED', 'Signées'], ['EFFECTIVE', 'En vigueur']];
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Registre central des fiches de cession POP'S (superadmin) : recherche, filtre, export CSV
export const CessionsRegistryCard = () => {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [items, setItems] = useState([]);
  const load = () => {
    const qs = new URLSearchParams();
    if (q) qs.set('q', q);
    if (status) qs.set('status', status);
    fetch(`${API}/admin/detaillant/cessions?${qs}`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { cessions: [] }))
      .then((d) => setItems(d.cessions || [])).catch(() => {});
  };
  useEffect(() => { load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const exportCsv = () => {
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = [['Référence', 'Boutique', 'Lot', 'Catégorie', 'Statut', 'Signataire', 'Signée le', 'Effet', 'Expiration'].map(esc).join(';')];
    items.forEach((c) => rows.push([c.reference, c.cedant?.company_name, c.lot_designation, c.category,
      c.status, c.signer_name || '', c.signed_at || '', c.effective_from || '', c.effective_until || ''].map(esc).join(';')));
    const blob = new Blob(['\ufeff' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'registre-cessions-pops.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="cessions-registry-card">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E]">Registre des fiches de cession ({items.length})</h3>
        <button type="button" onClick={exportCsv} disabled={items.length === 0} data-testid="cessions-export-csv"
          className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[11px] font-bold bg-[#D9B35A] text-[#2A1045] on-gold disabled:opacity-40">
          <FileSpreadsheet className="w-3.5 h-3.5" /> Export CSV
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <form className="relative flex-1 min-w-[180px]" onSubmit={(e) => { e.preventDefault(); load(); }}>
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-white/35" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Référence, boutique, lot, signataire…"
            data-testid="cessions-search-input"
            className="w-full h-8 pl-8 pr-3 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none" />
        </form>
        {STATUSES.map(([v, l]) => (
          <button key={v} type="button" onClick={() => setStatus(v)} data-testid={`cessions-status-${v || 'all'}`}
            className={`px-2.5 py-1 rounded-full text-[10px] font-bold border transition-colors ${status === v
              ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]' : 'text-white/60 border-white/20 hover:bg-white/10'}`}>
            {l}
          </button>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-white/40" data-testid="cessions-empty">Aucune fiche de cession.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-white/45 text-left">
              <th className="pr-2 pb-1">Référence</th><th className="pr-2">Boutique</th><th className="pr-2">Lot</th>
              <th className="pr-2">Statut</th><th className="pr-2">Signataire</th><th className="pr-2">Effet</th><th>Expiration</th>
            </tr></thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.reference} className="border-t border-white/[0.06] text-white/70"
                  data-testid={`cession-row-${c.reference}`}>
                  <td className="pr-2 py-1.5 font-bold text-white/85">{c.reference}</td>
                  <td className="pr-2">{c.cedant?.company_name}</td>
                  <td className="pr-2 max-w-[180px] truncate" title={c.lot_designation}>{c.lot_designation}</td>
                  <td className="pr-2">{c.status}</td>
                  <td className="pr-2">{c.signer_name || '—'}</td>
                  <td className="pr-2">{fmt(c.effective_from)}</td>
                  <td>{fmt(c.effective_until)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
