import { useCallback, useEffect, useState } from 'react';
import { BarChart3, Star, Check } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

const ServiceCreditRates = () => {
  const [rates, setRates] = useState(null);

  useEffect(() => {
    fetch(`${API}/logiscop-transport/admin/service-credit-rates`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setRates).catch(() => {});
  }, []);

  const save = async () => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/service-credit-rates`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ late_pct: Number(rates.late_pct), reserves_pct: Number(rates.reserves_pct) }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      toast.success(`Avoirs de service : retard ${rates.late_pct} % · réserves ${rates.reserves_pct} %`);
    } catch (e) { toast.error(e.message); }
  };

  if (!rates) return null;
  const inp = 'w-14 h-7 px-2 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white text-center';
  return (
    <div className="rounded-lg p-3 mt-2 bg-white/[0.04] border border-white/[0.08] flex flex-wrap items-center gap-2"
      data-testid="service-credit-rates">
      <p className="text-[11px] font-bold text-white/60">Avoirs de service (article 22) :</p>
      <label className="inline-flex items-center gap-1.5 text-[10px] text-white/50">
        Retard
        <input value={rates.late_pct} data-testid="credit-rate-late"
          onChange={(e) => setRates({ ...rates, late_pct: e.target.value.replace(/[^\d.]/g, '') })} className={inp} /> %
      </label>
      <label className="inline-flex items-center gap-1.5 text-[10px] text-white/50">
        Réserves
        <input value={rates.reserves_pct} data-testid="credit-rate-reserves"
          onChange={(e) => setRates({ ...rates, reserves_pct: e.target.value.replace(/[^\d.]/g, '') })} className={inp} /> %
      </label>
      <button type="button" onClick={save} data-testid="credit-rates-save"
        className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/70 hover:text-[#E9CF8E] border border-white/15 inline-flex items-center gap-1">
        <Check size={10} /> OK
      </button>
      <span className="text-[9px] text-white/35">Appliqués automatiquement à la clôture ePOD, cumulables, déduits du paiement en ligne.</span>
    </div>
  );
};

export const LogiscopTransportKpis = () => {
  const [kpi, setKpi] = useState(null);
  const [earn, setEarn] = useState(null);
  const [rate, setRate] = useState('');

  const load = useCallback(() => {
    fetch(`${API}/logiscop-transport/admin/dashboard`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setKpi).catch(() => {});
    fetch(`${API}/logiscop-transport/admin/operator-earnings`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setEarn(d); if (d) setRate(String(d.rate_percent)); }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveRate = async () => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/operator-share-rate`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ rate_percent: Number(rate) }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      toast.success(`Part opérateur fixée à ${rate} %`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (!kpi) return null;
  const cards = [
    ['CA transport (HT)', eur(kpi.ca.total_ht_cents), '#E9CF8E'],
    ['Encaissé (TTC)', eur(kpi.ca.paid_ttc_cents), '#A5E27E'],
    ['En attente (TTC)', eur(kpi.ca.outstanding_ttc_cents), '#FBBF24'],
    ['Factures en retard', `${kpi.ca.overdue_count} (${eur(kpi.ca.overdue_ttc_cents)})`,
      kpi.ca.overdue_count ? '#F87171' : '#A5E27E'],
    ['Ponctualité', kpi.orders.on_time_rate === null ? '—' : `${kpi.orders.on_time_rate} %`, '#93C5FD'],
    ['Taux de réserves', kpi.orders.reserves_rate === null ? '—' : `${kpi.orders.reserves_rate} %`,
      (kpi.orders.reserves_rate || 0) > 20 ? '#F87171' : '#A5E27E'],
    ['OT livrés / total', `${kpi.orders.delivered} / ${kpi.orders.total}`, '#F0ABFC'],
    ['Note moyenne', kpi.ratings.avg === null ? '—' : `${kpi.ratings.avg} ★ (${kpi.ratings.count})`, '#E9CF8E'],
  ];

  return (
    <div className="mb-4" data-testid="logiscop-kpis">
      <p className="flex items-center gap-2 text-[11px] font-bold text-white/60 mb-2">
        <BarChart3 size={12} className="text-[#D9B35A]" /> Indicateurs LOGI'SCOP
        {kpi.orders.temperature_incidents > 0 && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-300"
            data-testid="kpi-temp-incidents">{kpi.orders.temperature_incidents} incident(s) température</span>
        )}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        {cards.map(([label, value, color]) => (
          <div key={label} className="rounded-lg p-2.5 bg-white/[0.04] border border-white/[0.08]">
            <p className="text-[9px] uppercase tracking-wide text-white/40">{label}</p>
            <p className="text-sm font-bold" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {earn && (
        <div className="rounded-lg p-3 bg-white/[0.04] border border-white/[0.08]" data-testid="operator-earnings">          <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
            <p className="text-[11px] font-bold text-white/60">
              Rémunération des opérateurs (OT livrés) — total à reverser :{' '}
              <b className="text-[#E9CF8E]">{eur(earn.total_share_cents)}</b>
            </p>
            <span className="inline-flex items-center gap-1.5 text-[10px] text-white/50">
              Part opérateur
              <input value={rate} onChange={(e) => setRate(e.target.value.replace(/[^\d.]/g, ''))}
                data-testid="share-rate-input"
                className="w-14 h-7 px-2 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white text-center" />
              %
              <button type="button" onClick={saveRate} data-testid="share-rate-save"
                className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/70 hover:text-[#E9CF8E] border border-white/15 inline-flex items-center gap-1">
                <Check size={10} /> OK
              </button>
            </span>
          </div>
          {earn.operators.length === 0 ? (
            <p className="text-[10px] text-white/40">Aucun OT livré par un opérateur pour le moment.</p>
          ) : (
            <table className="w-full text-[11px]">
              <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
                <th className="py-1 pr-3">Opérateur</th><th className="py-1 pr-3">OT livrés</th>
                <th className="py-1 pr-3">CA transporté HT</th><th className="py-1 pr-3">Part ({earn.rate_percent} %)</th>
                <th className="py-1">Note moyenne</th></tr></thead>
              <tbody>
                {earn.operators.map((o) => (
                  <tr key={o.operator_id} className="border-b border-white/[0.04] text-white/75"
                    data-testid={`earnings-${o.operator_id}`}>
                    <td className="py-1 pr-3 font-semibold">{o.operator_name}</td>
                    <td className="py-1 pr-3">{o.delivered_count}</td>
                    <td className="py-1 pr-3">{eur(o.total_ht_cents)}</td>
                    <td className="py-1 pr-3 font-bold text-[#A5E27E]">{eur(o.share_cents)}</td>
                    <td className="py-1">
                      {o.avg_rating === null ? '—' : (
                        <span className="inline-flex items-center gap-1 text-[#E9CF8E]">
                          <Star size={11} fill="currentColor" /> {o.avg_rating}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <ServiceCreditRates />
    </div>
  );
};
