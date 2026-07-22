import { useEffect, useState } from 'react';
import { CalendarDays, TrendingUp, TrendingDown, Minus, FileDown } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const METRICS = [
  { key: 'revenue_eur', label: 'CA TTC', fmt: (v) => `${(v || 0).toFixed(0)} €` },
  { key: 'orders', label: 'Commandes' },
  { key: 'quotes', label: 'Devis' },
  { key: 'new_users', label: 'Nouveaux membres' },
  { key: 'prospect_sent', label: 'Emails prospection' },
  { key: 'testimonials', label: 'Témoignages' },
];

const Delta = ({ cur, prev }) => {
  if (prev === undefined || prev === null) return null;
  const diff = (cur || 0) - (prev || 0);
  if (diff === 0) return <span className="text-white/35 inline-flex items-center gap-0.5 text-[10px]"><Minus size={9} /> stable</span>;
  const up = diff > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-semibold ${up ? 'text-emerald-300' : 'text-red-300'}`}>
      {up ? <TrendingUp size={9} /> : <TrendingDown size={9} />} {up ? '+' : ''}{Number.isInteger(diff) ? diff : diff.toFixed(0)}
    </span>
  );
};

export const WeeklyReportWidget = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    fetch(`${API}/admin/reports/weekly/history`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);

  if (!items.length) return null;
  const latest = items[0];
  const prev = items[1];

  const downloadPdf = async () => {
    try {
      const r = await fetch(`${API}/admin/reports/weekly/${latest.week}/pdf`, { credentials: 'include' });
      if (!r.ok) throw new Error('Export impossible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rapport-hebdo-${latest.week}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { /* silencieux */ }
  };

  return (
    <div className="mb-8 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08]" data-testid="weekly-report-widget">
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <CalendarDays className="w-4 h-4 text-[#D9B35A]" /> Rapport hebdo d'activité
        </h3>
        <span className="px-2 py-0.5 rounded bg-[#D9B35A]/15 text-[#E9CF8E] text-xs font-semibold">Semaine {latest.week}</span>
        {prev && <span className="text-[10px] text-white/40">évolution vs semaine {prev.week}</span>}
        <button onClick={downloadPdf} data-testid="weekly-pdf-btn"
          className="ml-auto inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-[11px] font-semibold transition-colors hover:brightness-110"
          style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.4)', color: '#E9CF8E' }}>
          <FileDown size={11} /> PDF
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {METRICS.map((m) => (
          <div key={m.key} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`weekly-metric-${m.key}`}>
            <p className="text-lg font-bold text-white">{m.fmt ? m.fmt(latest.stats?.[m.key]) : (latest.stats?.[m.key] ?? 0)}</p>
            <p className="text-[10px] text-white/50">{m.label}</p>
            <Delta cur={latest.stats?.[m.key]} prev={prev?.stats?.[m.key]} />
          </div>
        ))}
      </div>
      {items.length > 2 && (
        <p className="mt-3 text-[10px] text-white/35">
          Historique : {items.slice(0, 6).map((i) => `${i.week} (${(i.stats?.revenue_eur || 0).toFixed(0)} €)`).join(' · ')}
        </p>
      )}
    </div>
  );
};
