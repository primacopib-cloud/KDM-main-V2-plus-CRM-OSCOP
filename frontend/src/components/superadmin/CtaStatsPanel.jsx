import { useEffect, useState } from 'react';
import { MousePointerClick, Download } from 'lucide-react';
import { toast } from 'sonner';
import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { API, getAuthHeaders } from '../../services/http';

const TrendChart = ({ points }) => {
  if (!points || points.every((p) => !p.clicks && !p.paid)) return null;
  return (
    <div className="mb-4" data-testid="cta-trend-chart">
      <p className="text-[10px] uppercase tracking-wider text-white/35 mb-1.5">Tendance hebdomadaire (12 dernières semaines)</p>
      <ResponsiveContainer width="100%" height={160}>
        <ComposedChart data={points} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="week" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#1F0A33', border: '1px solid rgba(217,179,90,0.35)', borderRadius: 10, fontSize: 11 }}
            labelStyle={{ color: '#E9CF8E' }} itemStyle={{ color: '#fff' }}
            labelFormatter={(w, payload) => `${w} — semaine du ${payload?.[0]?.payload?.start || ''}`}
            formatter={(v, name) => [v, name === 'clicks' ? 'Clics adhésion' : 'Adhésions payées']}
          />
          <Bar dataKey="clicks" fill="#D9B35A" radius={[3, 3, 0, 0]} maxBarSize={22} />
          <Line type="monotone" dataKey="paid" stroke="#7BC94E" strokeWidth={2} dot={{ r: 2.5, fill: '#7BC94E' }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export const CtaStatsPanel = () => {
  const [data, setData] = useState(null);
  const [trend, setTrend] = useState(null);
  const [podiumPeriod, setPodiumPeriod] = useState('tout');

  useEffect(() => {
    const opts = { headers: getAuthHeaders(), credentials: 'include' };
    fetch(`${API}/admin/cta-stats`, opts)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
    fetch(`${API}/admin/cta-stats/trend?weeks=12`, opts)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setTrend(d?.points || null))
      .catch(() => {});
  }, []);

  if (!data) return null;
  const max = Math.max(...data.stats.map((s) => s.total), 1);
  const periodKey = { '7j': 'last7', '30j': 'last30', tout: 'total' }[podiumPeriod];
  const podium = data.stats
    .filter((s) => s.cta_id.startsWith('territoire_') && s[periodKey] > 0)
    .sort((a, b) => b[periodKey] - a[periodKey])
    .slice(0, 3);

  const exportCsv = async () => {
    try {
      const r = await fetch(`${API}/admin/cta-stats/export`, { headers: getAuthHeaders(), credentials: 'include' });
      if (!r.ok) throw new Error('Export impossible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversion-cta-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mb-4" data-testid="cta-stats-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <MousePointerClick className="w-4 h-4" /> Suivi de conversion
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-white/45" data-testid="cta-total-clicks">{data.total_clicks} clics · {data.total_paid} adhésion(s) payée(s)</span>
          <button type="button" onClick={exportCsv} data-testid="export-cta-csv-btn"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15 transition-colors">
            <Download className="w-3 h-3" /> Export CSV
          </button>
        </div>
      </div>
      {data.total_clicks === 0 ? (
        <p className="text-xs text-white/45">Aucun clic enregistré pour le moment.</p>
      ) : (
        <>
        {(podium.length > 0 || podiumPeriod !== 'tout') && (
          <div className="mb-4" data-testid="territory-podium">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
              <p className="text-[10px] uppercase tracking-wider text-white/35 m-0">🏆 Territoires les plus cliqués (« Voir les offres de la zone »)</p>
              <div className="flex items-center gap-1" data-testid="podium-period-switch">
                {[['7j', '7 j'], ['30j', '30 j'], ['tout', 'Depuis le début']].map(([key, lbl]) => (
                  <button key={key} type="button" onClick={() => setPodiumPeriod(key)}
                    data-testid={`podium-period-${key}`} aria-pressed={podiumPeriod === key}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                      podiumPeriod === key
                        ? 'bg-[#D9B35A] text-black border-[#D9B35A]'
                        : 'text-white/50 border-white/15 hover:text-white hover:border-white/35'}`}>
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            {podium.length === 0 ? (
              <p className="text-[10px] text-white/35 m-0" data-testid="podium-empty">Aucun clic territoire sur cette période.</p>
            ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {podium.map((s, i) => (
                <div key={s.cta_id} data-testid={`territory-podium-${i}`}
                  className={`flex items-center gap-2.5 rounded-xl px-3 py-2 border ${
                    i === 0 ? 'bg-[#D9B35A]/10 border-[#D9B35A]/35' : 'bg-white/[0.04] border-white/10'}`}>
                  <span className="text-xl" aria-hidden="true">{['🥇', '🥈', '🥉'][i]}</span>
                  <div className="min-w-0">
                    <p className="text-[12px] font-bold text-white truncate m-0">
                      {s.label.replace('Voir les offres — ', '').replace(' (/kdmarche)', '')}
                    </p>
                    <p className="text-[10px] text-white/50 m-0">
                      {s[periodKey]} clic{s[periodKey] > 1 ? 's' : ''}
                      {podiumPeriod === '7j' ? ' sur 7 j' : podiumPeriod === '30j' ? ' sur 30 j' : ' au total'}
                      {s.paid > 0 && <span className="text-[#7BC94E] font-bold"> · {s.paid} commande{s.paid > 1 ? 's' : ''}</span>}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            )}
          </div>
        )}
        <TrendChart points={trend} />
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-white/35">
            <span className="flex-1">Bouton</span>
            <span className="w-10 text-right">7 j</span>
            <span className="w-10 text-right">30 j</span>
            <span className="w-12 text-right">Clics</span>
            <span className="w-14 text-right">Payées</span>
            <span className="w-12 text-right">Taux</span>
          </div>
          {data.stats.map((s) => (
            <div key={s.cta_id} className="flex items-center gap-3" data-testid={`cta-stat-${s.cta_id}`}>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-white/70 truncate">{s.label}</div>
                <div className="h-1.5 rounded bg-white/[0.05] mt-1 overflow-hidden">
                  <div className="h-full rounded" style={{ width: `${Math.max((s.total / max) * 100, 2)}%`, background: 'linear-gradient(90deg,#D9B35A,#b8933e)' }} />
                </div>
              </div>
              <span className="w-10 text-right text-[11px] text-white/55">{s.last7}</span>
              <span className="w-10 text-right text-[11px] text-white/55">{s.last30}</span>
              <span className="w-12 text-right text-[12px] font-bold text-[#E9CF8E]">{s.total}</span>
              <span className="w-14 text-right text-[12px] font-bold text-[#7BC94E]" data-testid={`cta-paid-${s.cta_id}`}>{s.paid}</span>
              <span className="w-12 text-right text-[11px] text-white/70">{s.rate === null ? '—' : `${s.rate} %`}</span>
            </div>
          ))}
          <p className="text-[10px] text-white/35 pt-1">
            « Payées » = adhésions au paiement confirmé attribuées au dernier bouton cliqué (fenêtre de 24 h).
            Pour les territoires : commandes passées dans la zone visitée après le clic (même fenêtre).
          </p>
        </div>
        </>
      )}
    </div>
  );
};
