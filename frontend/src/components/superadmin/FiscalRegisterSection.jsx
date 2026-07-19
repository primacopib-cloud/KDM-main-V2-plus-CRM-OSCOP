import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Download, BookOpenCheck } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => `${(c / 100).toFixed(2).replace('.', ',')} €`;

export const RevenueChart = ({ byMonth }) => {
  const data = Object.entries(byMonth || {}).map(([m, v]) => ({ mois: m, TTC: +(v.ttc_cents / 100).toFixed(2), HT: +(v.ht_cents / 100).toFixed(2) })).sort((a, b) => a.mois.localeCompare(b.mois));
  if (data.length < 2) return null;
  return (
    <div className="glass-panel-soft rounded-[14px] p-3" data-testid="revenue-chart">
      <p className="text-[11px] font-semibold text-[#D9B35A] mb-2">Évolution mensuelle des revenus (€)</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
          <XAxis dataKey="mois" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
          <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.4)', borderRadius: 10, fontSize: 11 }} labelStyle={{ color: '#E9CF8E' }} />
          <Line type="monotone" dataKey="TTC" stroke="#D9B35A" strokeWidth={2.5} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="HT" stroke="#60A5FA" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export const FiscalRegisterSection = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/accounting/fiscal-register`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  const exportCsv = async () => {
    const r = await fetch(`${API}/admin/accounting/fiscal-register/export.csv`, { headers: getAuthHeaders(), credentials: 'include' });
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'registre-fiscal.csv'; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="glass-panel-soft rounded-[14px] p-3" data-testid="fiscal-register">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-semibold text-[#D9B35A] flex items-center gap-1.5">
          <BookOpenCheck className="w-3.5 h-3.5" /> Registre fiscal — récapitulatif par source
        </p>
        <button type="button" onClick={exportCsv} data-testid="fiscal-export-csv"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold"
          style={{ background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}>
          <Download className="w-3 h-3" /> Export CSV
        </button>
      </div>
      <table className="w-full text-[11px]">
        <thead><tr className="text-white/45 text-left">
          <th className="pb-1.5">Source</th><th className="text-right pb-1.5">Ops</th>
          <th className="text-right pb-1.5">HT</th><th className="text-right pb-1.5">TVA</th><th className="text-right pb-1.5">TTC</th></tr></thead>
        <tbody>
          {Object.entries(data.sources).map(([k, v]) => (
            <tr key={k} className="border-t border-white/5 text-white/75">
              <td className="py-1.5">{(data.labels || {})[k] || k}</td>
              <td className="text-right">{v.count}</td>
              <td className="text-right">{eur(v.ht_cents)}</td>
              <td className="text-right">{eur(v.vat_cents)}</td>
              <td className="text-right font-semibold">{eur(v.ttc_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {Object.keys(data.vat_by_country || {}).length > 0 && (
        <p className="text-[10px] text-white/45 mt-2">
          TVA collectée par territoire : {Object.entries(data.vat_by_country).map(([c, v]) => `${c} ${eur(v.vat_cents)}`).join(' · ')}
        </p>
      )}
      {(data.snapshots || []).length > 0 && (
        <p className="text-[10px] text-white/35 mt-1">
          Snapshots mensuels enregistrés : {data.snapshots.map((s) => s.month).join(', ')}
        </p>
      )}
    </div>
  );
};
