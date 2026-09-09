import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { BadgeCheck, Copy, Download, Eye, EyeOff, FileSpreadsheet, KeyRound, ScrollText } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const frDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch { return iso || '—'; } };

export const ApiSubscriptionsPanel = () => {
  const [data, setData] = useState({ items: [], active_count: 0, total_eur: 0, annual_price_eur: 2500 });
  const [revealed, setRevealed] = useState({});
  const [showLog, setShowLog] = useState(false);
  const [calls, setCalls] = useState(null);
  const [logQ, setLogQ] = useState('');
  const [stats, setStats] = useState(null);

  const loadCalls = (q = '') => {
    fetch(`${API}/admin/api-subscriptions/calls?limit=50&q=${encodeURIComponent(q)}`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setCalls(d.calls || []))
      .catch(() => setCalls([]));
  };
  const toggleLog = () => {
    const next = !showLog;
    setShowLog(next);
    if (next) loadCalls(logQ);
  };
  const onFilterChange = (v) => { setLogQ(v); loadCalls(v); };

  const load = useCallback(() => {
    fetch(`${API}/admin/api-subscriptions`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => {});
    fetch(`${API}/admin/api-subscriptions/stats`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const copyKey = (s) => { navigator.clipboard.writeText(s.api_key); toast.success('Clé API copiée'); };

  const downloadInvoice = async (s) => {
    const r = await fetch(`${API}/admin/api-subscriptions/${s.id}/invoice.pdf`, { credentials: 'include' });
    if (!r.ok) return toast.error('Facture indisponible');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `facture-${s.reference}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const exportCsv = async () => {
    const r = await fetch(`${API}/admin/api-subscriptions/export`, { credentials: 'include' });
    if (!r.ok) return toast.error('Export impossible');
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'abonnements-api.csv';
    a.click();
    URL.revokeObjectURL(a.href);
    toast.success('Export CSV téléchargé');
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="api-subscriptions-panel">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-display text-lg text-white flex items-center gap-2 m-0">
          <KeyRound size={16} style={{ color: '#D9B35A' }} /> Abonnements API annuels
          <span className="text-sm font-normal text-white/50">({data.items.length})</span>
        </h3>
        <button onClick={exportCsv} data-testid="api-subs-export-csv-btn"
          className="h-8 px-3 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10">
          <FileSpreadsheet size={13} /> CSV
        </button>
      </div>
      <p className="text-xs text-white/45 mb-4" data-testid="api-subs-summary">
        {data.active_count} abonnement(s) actif(s) · {Number(data.total_eur).toLocaleString('fr-FR')} € encaissés ·
        tarif annuel {Number(data.annual_price_eur).toLocaleString('fr-FR')} €
      </p>
      {stats && (
        <div className="mb-4 p-3 rounded-xl bg-white/[0.03] border border-white/10" data-testid="api-subs-chart">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-bold uppercase tracking-wide text-white/50 m-0">Appels API par jour — 30 derniers jours</p>
            <p className="text-[11px] text-[#E9CF8E] font-semibold m-0" data-testid="api-subs-chart-total">
              {Number(stats.total_30d).toLocaleString('fr-FR')} appel(s)
            </p>
          </div>
          <div className="flex items-end gap-[2px] h-16">
            {stats.daily.map((d) => {
              const max = Math.max(...stats.daily.map((x) => x.count), 1);
              return (
                <div key={d.day} title={`${d.day.slice(8, 10)}/${d.day.slice(5, 7)} — ${d.count} appel(s)`}
                  data-testid={`api-chart-day-${d.day}`}
                  className={`flex-1 rounded-t-sm ${d.count ? 'bg-gradient-to-t from-[#8CC63E] to-[#D9B35A]' : 'bg-white/[0.07]'}`}
                  style={{ height: d.count ? `${Math.max(8, (d.count / max) * 100)}%` : '3px' }} />
              );
            })}
          </div>
          <div className="flex justify-between text-[9px] text-white/30 mt-1">
            <span>{stats.daily[0] && `${stats.daily[0].day.slice(8, 10)}/${stats.daily[0].day.slice(5, 7)}`}</span>
            <span>aujourd'hui</span>
          </div>
          {stats.top_endpoints?.length > 0 && (
            <div className="mt-3 pt-2 border-t border-white/10" data-testid="api-top-endpoints">
              <p className="text-[10px] font-bold uppercase tracking-wide text-white/45 m-0 mb-1.5">Endpoints les plus appelés</p>
              <div className="space-y-1">
                {stats.top_endpoints.map((e, i) => (
                  <div key={e.path} className="flex items-center gap-2 text-[11px]" data-testid={`api-top-endpoint-${i}`}>
                    <span className="w-5 text-center font-bold text-[#D9B35A]">{i + 1}.</span>
                    <code className="text-white/80 flex-1 truncate">{e.path}</code>
                    <span className="text-[#B6E27A] font-semibold">{e.count} appel(s)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div className="space-y-2">
        {data.items.map((s) => (
          <div key={s.id} className="p-3 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`api-sub-row-${s.reference}`}>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-sm text-white font-medium">{s.reference}</span>
              {s.status === 'ACTIVE' ? (
                <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                  <BadgeCheck size={11} /> ACTIF
                </span>
              ) : s.status === 'EXPIRED' ? (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-bold">EXPIRÉ — CLÉ DÉSACTIVÉE</span>
              ) : (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">EN ATTENTE DE PAIEMENT</span>
              )}
              <span className="text-xs text-white/60">{s.email}{s.company ? ` · ${s.company}` : ''}</span>
              <span className="text-xs text-white/40 ml-auto">
                {Number(s.amount_eur).toLocaleString('fr-FR')} € · souscrit le {frDate(s.created_at)}
                {s.paid_at ? ` · payé le ${frDate(s.paid_at)}` : ''}
                {s.valid_until ? ` · valide jusqu'au ${frDate(s.valid_until)}` : ''}
              </span>
            </div>
            {s.api_key && (
              <div className="flex items-center gap-2 mt-2">
                <code className="text-[11px] text-[#B6E27A] bg-black/30 px-2 py-1 rounded-lg flex-1 break-all" data-testid={`api-sub-key-${s.reference}`}>
                  {revealed[s.id] ? s.api_key : `${s.api_key_prefix || ''}${'•'.repeat(20)}`}
                </code>
                <button onClick={() => setRevealed((r) => ({ ...r, [s.id]: !r[s.id] }))}
                  data-testid={`api-sub-key-reveal-${s.reference}`}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-white/70" title={revealed[s.id] ? 'Masquer' : 'Révéler'}>
                  {revealed[s.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
                <button onClick={() => copyKey(s)} className="p-1.5 rounded-lg hover:bg-white/10 text-white/70" title="Copier"
                  data-testid={`api-sub-key-copy-${s.reference}`}>
                  <Copy size={13} />
                </button>
                <button onClick={() => downloadInvoice(s)} data-testid={`api-sub-invoice-${s.reference}`}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-[#D9B35A]" title="Facture acquittée PDF">
                  <Download size={13} />
                </button>
              </div>
            )}
          </div>
        ))}
        {!data.items.length && (
          <p className="text-sm text-white/40 py-4 text-center">Aucun abonnement API souscrit pour le moment.</p>
        )}
      </div>
      <div className="mt-4 pt-3 border-t border-white/10">
        <button onClick={toggleLog} data-testid="api-subs-log-toggle"
          className="text-xs font-bold text-white/60 hover:text-white inline-flex items-center gap-1.5">
          <ScrollText size={13} className="text-[#D9B35A]" /> Journal des appels API {showLog ? '▾' : '▸'}
        </button>
        {showLog && (
          <input value={logQ} onChange={(e) => onFilterChange(e.target.value)}
            placeholder="Filtrer par abonné, référence ou endpoint…" data-testid="api-subs-log-filter"
            className="mt-2 w-full h-8 px-2.5 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white placeholder:text-white/30" />
        )}
        {showLog && (
          <div className="mt-2 space-y-1 max-h-64 overflow-y-auto" data-testid="api-subs-log-list">
            {calls === null && <p className="text-xs text-white/40 m-0 py-2">Chargement…</p>}
            {calls?.map((c, i) => (
              <div key={i} className="flex flex-wrap items-center gap-x-2 text-[11px] py-1 px-2 rounded-lg bg-white/[0.03]">
                <span className={`px-1.5 py-0.5 rounded font-bold ${c.method === 'GET' ? 'bg-[#8CC63E]/15 text-[#B6E27A]' : 'bg-amber-400/15 text-amber-300'}`}>{c.method}</span>
                <code className="text-white/80">{c.path}</code>
                <span className="text-white/45">{c.email} · {c.reference}</span>
                <span className="text-white/35 ml-auto">{new Date(c.ts).toLocaleString('fr-FR')}</span>
              </div>
            ))}
            {calls?.length === 0 && <p className="text-xs text-white/40 m-0 py-2">{logQ ? 'Aucun appel ne correspond au filtre.' : 'Aucun appel API enregistré par les abonnés.'}</p>}
          </div>
        )}
      </div>
    </div>
  );
};
