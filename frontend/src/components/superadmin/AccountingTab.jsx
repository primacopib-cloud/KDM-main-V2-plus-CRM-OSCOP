import { useCallback, useEffect, useState } from 'react';
import { Calculator, Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (cents) => `${(cents / 100).toFixed(2).replace('.', ',')} €`;

const PERIODS = [
  { days: 30, label: '30 jours' },
  { days: 90, label: '90 jours' },
  { days: 365, label: '12 mois' },
  { days: 0, label: 'Tout' },
];

export const AccountingTab = () => {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(90);
  const [opType, setOpType] = useState('all');
  const [loading, setLoading] = useState(true);

  const dateFrom = useCallback((d) => {
    if (!d) return '2020-01-01';
    return new Date(Date.now() - d * 86400000).toISOString().slice(0, 10);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/admin/accounting/journal?date_from=${dateFrom(days)}&op_type=${opType}`,
      { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => toast.error('Erreur de chargement du journal'))
      .finally(() => setLoading(false));
  }, [days, opType, dateFrom]);

  const exportCsv = async () => {
    try {
      const r = await fetch(`${API}/admin/accounting/export.csv?date_from=${dateFrom(days)}`,
        { headers: getAuthHeaders(), credentials: 'include' });
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'journal-comptable.csv'; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Échec de l'export"); }
  };

  const labels = data?.kind_labels || {};
  return (
    <div className="space-y-4" data-testid="accounting-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Calculator className="w-4 h-4 text-[#D9B35A]" /> Comptabilité analytique
        </h2>
        <div className="flex items-center gap-2">
          {PERIODS.map((p) => (
            <button key={p.days} type="button" onClick={() => setDays(p.days)}
              data-testid={`acct-period-${p.days}`}
              className={`px-2.5 py-1 rounded-lg text-[10.5px] font-bold transition-colors ${
                days === p.days ? 'bg-[#D9B35A] text-[#1F0A33]' : 'bg-white/10 text-white/55 hover:text-white/80'
              }`}>{p.label}</button>
          ))}
          <button type="button" onClick={exportCsv} data-testid="acct-export-csv"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
            style={{ background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}>
            <Download className="w-3.5 h-3.5" /> Export CSV comptable
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
      ) : !data ? null : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="acct-totals">
            {[
              { label: 'Total HT', v: eur(data.totals.ht_cents), c: '#60A5FA' },
              { label: 'TVA collectée', v: eur(data.totals.vat_cents), c: '#E9CF8E' },
              { label: 'Total TTC', v: eur(data.totals.ttc_cents), c: '#7BC94E' },
              { label: 'Opérations', v: String(data.totals.count), c: '#9CA3AF' },
            ].map((k) => (
              <div key={k.label} className="glass-panel-soft rounded-[14px] p-3">
                <p className="text-[10.5px] text-white/50">{k.label}</p>
                <p className="text-lg font-bold" style={{ color: k.c }}>{k.v}</p>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <div className="glass-panel-soft rounded-[14px] p-3">
              <p className="text-[11px] font-semibold text-[#D9B35A] mb-2">Ventilation par type d'opération</p>
              <table className="w-full text-[11px]">
                <thead><tr className="text-white/45 text-left">
                  <th className="pb-1.5">Type</th><th className="text-right pb-1.5">Ops</th>
                  <th className="text-right pb-1.5">HT</th><th className="text-right pb-1.5">TVA</th><th className="text-right pb-1.5">TTC</th></tr></thead>
                <tbody>
                  {Object.entries(data.by_type).map(([k, v]) => (
                    <tr key={k} className="border-t border-white/5 text-white/75">
                      <td className="py-1.5">
                        <button type="button" onClick={() => setOpType(opType === k ? 'all' : k)}
                          className={`hover:text-[#E9CF8E] ${opType === k ? 'text-[#E9CF8E] font-bold' : ''}`}>
                          {labels[k] || k}
                        </button>
                      </td>
                      <td className="text-right">{v.count}</td>
                      <td className="text-right">{eur(v.ht_cents)}</td>
                      <td className="text-right">{eur(v.vat_cents)}</td>
                      <td className="text-right font-semibold">{eur(v.ttc_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="glass-panel-soft rounded-[14px] p-3">
              <p className="text-[11px] font-semibold text-[#D9B35A] mb-2">Totaux par mois</p>
              <table className="w-full text-[11px]">
                <thead><tr className="text-white/45 text-left">
                  <th className="pb-1.5">Mois</th><th className="text-right pb-1.5">Ops</th>
                  <th className="text-right pb-1.5">HT</th><th className="text-right pb-1.5">TVA</th><th className="text-right pb-1.5">TTC</th></tr></thead>
                <tbody>
                  {Object.entries(data.by_month).slice(0, 12).map(([m, v]) => (
                    <tr key={m} className="border-t border-white/5 text-white/75">
                      <td className="py-1.5">{m}</td><td className="text-right">{v.count}</td>
                      <td className="text-right">{eur(v.ht_cents)}</td>
                      <td className="text-right">{eur(v.vat_cents)}</td>
                      <td className="text-right font-semibold">{eur(v.ttc_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="glass-panel-soft rounded-[14px] p-3" data-testid="acct-journal">
            <p className="text-[11px] font-semibold text-[#D9B35A] mb-2">
              Journal des opérations {opType !== 'all' ? `— ${labels[opType] || opType}` : ''} ({data.entries.length})
            </p>
            <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
              <table className="w-full text-[11px]">
                <thead><tr className="text-white/45 text-left sticky top-0" style={{ background: '#241038' }}>
                  <th className="py-1.5 pr-2">Date</th><th className="pr-2">Type</th><th className="pr-2">Libellé</th>
                  <th className="pr-2">Pays</th><th className="text-right pr-2">HT</th>
                  <th className="text-right pr-2">TVA</th><th className="text-right">TTC</th></tr></thead>
                <tbody>
                  {data.entries.map((e, i) => (
                    <tr key={`${e.ref}-${i}`} className="border-t border-white/5 text-white/75">
                      <td className="py-1.5 pr-2 whitespace-nowrap">{String(e.date).slice(0, 10)}</td>
                      <td className="pr-2 whitespace-nowrap">{labels[e.type] || e.type}</td>
                      <td className="pr-2">{e.label}</td>
                      <td className="pr-2">{e.country}</td>
                      <td className={`text-right pr-2 ${e.ht_cents < 0 ? 'text-red-400' : ''}`}>{eur(e.ht_cents)}</td>
                      <td className="text-right pr-2">{eur(e.vat_cents)}</td>
                      <td className={`text-right font-semibold ${e.ttc_cents < 0 ? 'text-red-400' : ''}`}>{eur(e.ttc_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
