import { useEffect, useState } from 'react';
import { Download, Eye, FileSpreadsheet, Search, X } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';
import { downloadAuthedPdf } from '../../detaillant/DetaillantConventionCard';

const STATUSES = [['', 'Toutes'], ['DRAFT', 'À signer'], ['SIGNED', 'Signées'], ['EFFECTIVE', 'En vigueur']];
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Registre central des fiches de cession POP'S (superadmin) : recherche, filtre, export CSV
export const CessionsRegistryCard = () => {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [items, setItems] = useState([]);
  const [detail, setDetail] = useState(null);
  const [stats, setStats] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [shop, setShop] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const load = () => {
    const qs = new URLSearchParams();
    if (q) qs.set('q', q);
    if (status) qs.set('status', status);
    if (shop) qs.set('shop', shop);
    if (dateFrom) qs.set('date_from', dateFrom);
    if (dateTo) qs.set('date_to', dateTo);
    fetch(`${API}/admin/detaillant/cessions?${qs}`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { cessions: [] }))
      .then((d) => { setItems(d.cessions || []); setStats(d.stats || null); setMonthly(d.monthly || []); }).catch(() => {});
  };
  useEffect(() => { load(); }, [status, dateFrom, dateTo]); // eslint-disable-line react-hooks/exhaustive-deps

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
      {stats && (
        <div className="flex flex-wrap gap-2 mb-3" data-testid="cessions-stats">
          <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-amber-500/12 text-amber-300 border border-amber-400/30"
            data-testid="cessions-stat-draft">À signer : {stats.DRAFT}</span>
          <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-sky-500/12 text-sky-300 border border-sky-400/30"
            data-testid="cessions-stat-signed">Signées : {stats.SIGNED}</span>
          <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/12 text-emerald-300 border border-emerald-400/30"
            data-testid="cessions-stat-effective">En vigueur : {stats.EFFECTIVE}</span>
        </div>
      )}
      {monthly.length > 0 && (
        <div className="mb-3" data-testid="cessions-monthly-chart">
          <p className="text-[10px] font-bold text-white/50 uppercase tracking-wide mb-1.5">Fiches signées par mois</p>
          <div className="flex items-end gap-1.5 h-20">
            {monthly.map((m) => {
              const max = Math.max(...monthly.map((x) => x.n));
              return (
                <div key={m.month} className="flex flex-col items-center gap-1 flex-1 min-w-0"
                  data-testid={`cessions-month-${m.month}`} title={`${m.month} : ${m.n} signée(s)`}>
                  <span className="text-[9px] font-bold text-[#F2D07A]">{m.n}</span>
                  <div className="w-full max-w-8 rounded-t bg-gradient-to-t from-[#D9B35A]/50 to-[#D9B35A]"
                    style={{ height: `${Math.max(6, Math.round((m.n / max) * 56))}px` }} />
                  <span className="text-[8px] text-white/45">{m.month.slice(5)}/{m.month.slice(2, 4)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
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
        <input value={shop} onChange={(e) => setShop(e.target.value)} onBlur={load}
          onKeyDown={(e) => e.key === 'Enter' && load()}
          placeholder="Boutique…" data-testid="cessions-shop-input"
          className="h-8 w-32 px-2.5 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white placeholder-white/30 outline-none" />
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
          data-testid="cessions-date-from" title="Du"
          className="h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white/70 outline-none" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
          data-testid="cessions-date-to" title="Au"
          className="h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white/70 outline-none" />
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-white/40" data-testid="cessions-empty">Aucune fiche de cession.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-white/45 text-left">
              <th className="pr-2 pb-1">Référence</th><th className="pr-2">Boutique</th><th className="pr-2">Lot</th>
              <th className="pr-2">Statut</th><th className="pr-2">Signataire</th><th className="pr-2">Effet</th><th className="pr-2">Expiration</th><th>Actions</th>
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
                  <td className="pr-2">{fmt(c.effective_until)}</td>
                  <td className="whitespace-nowrap">
                    <button type="button" onClick={() => setDetail(c)} title="Voir le détail"
                      data-testid={`cession-detail-btn-${c.reference}`}
                      className="inline-flex items-center justify-center w-6 h-6 rounded-md text-white/55 hover:text-white hover:bg-white/10">
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                    <button type="button" title="Télécharger le PDF"
                      onClick={() => downloadAuthedPdf(`/admin/detaillant/cessions/${c.reference}/pdf`, `${c.reference}.pdf`)}
                      data-testid={`cession-pdf-btn-${c.reference}`}
                      className="inline-flex items-center justify-center w-6 h-6 rounded-md text-[#F2D07A] hover:bg-[#D9B35A]/15">
                      <Download className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setDetail(null)}>
          <div className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-white/15 bg-[#241238] p-5"
            data-testid="cession-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-3">
              <h4 className="text-sm font-bold text-[#E9CF8E]">Fiche de cession {detail.reference}</h4>
              <button onClick={() => setDetail(null)} data-testid="cession-detail-close"
                className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-2 text-[11px] text-white/75">
              <p><b className="text-white/90">Cédant :</b> {detail.cedant?.company_name} — {detail.cedant?.locality} ({detail.cedant?.country_code})</p>
              <p><b className="text-white/90">Cessionnaire :</b> {detail.cessionnaire}</p>
              <p><b className="text-white/90">Lot :</b> {detail.lot_designation} · {detail.qty_lots} lot(s) ×3 · {detail.category} · {detail.condition === 'NEW' ? 'Neuf' : 'Occasion'}</p>
              <p><b className="text-white/90">Produits :</b> {(detail.products || []).map((p) => `${p.name} ×${p.qty}${p.dlc ? ` (DLC ${p.dlc})` : ''}`).join(' · ')}</p>
              <p><b className="text-white/90">Valorisation :</b> {detail.valuation?.lot_price} {detail.valuation?.currency} → {detail.valuation?.final_price} {detail.valuation?.currency} (-{Number(detail.valuation?.discount_pct || 0).toFixed(0)} %)</p>
              <p><b className="text-white/90">Effet :</b> {fmt(detail.effective_from)} · <b className="text-white/90">Expiration :</b> {fmt(detail.effective_until)}</p>
              <div>
                <b className="text-white/90">Déclarations :</b>
                <ul className="mt-1 space-y-0.5">
                  {(detail.declarations || []).map((d) => (
                    <li key={d}>{(detail.declarations_checked || []).includes(d) ? '☑' : '☐'} {d}</li>
                  ))}
                </ul>
              </div>
              <p><b className="text-white/90">Signature :</b> {detail.signer_name
                ? `${detail.signer_name} le ${fmt(detail.signed_at)} — ${detail.status}` : 'Non signée (DRAFT)'}</p>
            </div>
            <button type="button" data-testid="cession-detail-pdf"
              onClick={() => downloadAuthedPdf(`/admin/detaillant/cessions/${detail.reference}/pdf`, `${detail.reference}.pdf`)}
              className="mt-4 inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[11px] font-bold bg-[#D9B35A] text-[#2A1045] on-gold">
              <Download className="w-3.5 h-3.5" /> Télécharger le PDF
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
