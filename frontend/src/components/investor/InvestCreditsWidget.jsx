import { useState, useEffect, useCallback } from 'react';
import { Coins, AlertTriangle, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const fmtUc = (n) => (n ?? 0).toLocaleString('fr-FR') + ' uc';

// Solde CREDI'SCOP-INVEST temps réel + historique + alertes + packs
export const InvestCreditsWidget = () => {
  const [data, setData] = useState(null);
  const [none, setNone] = useState(false);

  const load = useCallback(() => {
    fetch(`${API_URL}/api/investor-plans/my-credits`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData)
      .catch(() => setNone(true));
  }, []);

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    const packSession = params.get('pack_session_id');
    if (packSession) {
      fetch(`${API_URL}/api/investor-plans/pack-status/${packSession}`, { headers: getAuthHeaders() })
        .then((r) => r.json())
        .then((d) => { if (d.status === 'CREDITED') { toast.success(`${fmtUc(d.credits_uc)} crédités !`); load(); } })
        .catch(() => {});
    }
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  const buyPack = async (key) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/buy-pack`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ pack_key: key }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      window.location.href = d.checkout_url;
    } catch (e) { toast.error(e.message); }
  };

  const exportFinancings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/my-financings/pdf`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Export impossible');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'financements-crediscop-invest.pdf'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  if (none || !data) return null;
  const warning = data.alert === 'ALMOST';
  const reached = data.alert === 'REACHED';
  const suspended = data.account_status === 'SUSPENDED';
  return (
    <div className="rounded-[20px] p-5 mb-5 bg-white/[0.03] border border-[#D9B35A]/25" data-testid="invest-credits-widget">
      {suspended && (
        <div className="rounded-xl px-3 py-2 mb-3 flex items-start gap-2 text-xs bg-red-500/10 border border-red-400/40 text-red-300" data-testid="invest-suspended-banner">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>Capacité de financement <b>suspendue</b> après 2 échecs de prélèvement consécutifs. Mettez à jour votre carte bancaire : elle sera rétablie au prochain paiement réussi.</span>
        </div>
      )}
      <div className="flex items-center gap-2 mb-2">
        <Coins className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">CREDI'SCOP-INVEST — plan {data.plan}</h3>
        <span className="ml-auto text-[11px] text-white/40">quota mensuel {fmtUc(data.monthly_invest_uc)}</span>
      </div>
      <div className="flex items-end gap-4 flex-wrap mb-2">
        <p className="m-0"><span className="text-2xl font-bold text-white" data-testid="invest-balance">{fmtUc(data.balance_uc)}</span>
          <span className="text-white/40 text-xs ml-1.5">de capacité restante</span></p>
        <p className="m-0 text-xs text-white/50">Consommé : {fmtUc(data.consumed_uc)} ({data.usage_percent} %)</p>
      </div>
      <div className="h-2 rounded-full bg-white/[0.08] overflow-hidden mb-2">
        <div className={`h-full ${reached ? 'bg-red-500' : warning ? 'bg-amber-400' : 'bg-[#8CC63E]'}`}
          style={{ width: `${Math.min(100, data.usage_percent)}%` }}></div>
      </div>
      {(warning || reached) && (
        <div className={`rounded-xl px-3 py-2 mb-3 flex items-start gap-2 text-xs ${reached ? 'bg-red-500/10 border border-red-400/40 text-red-300' : 'bg-amber-500/10 border border-amber-400/40 text-amber-300'}`}
          data-testid="invest-credits-alert">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{reached ? 'Capacité mensuelle atteinte — rechargez avec un pack Crédits INVEST pour continuer à financer.' : 'Capacité mensuelle presque atteinte (≥ 90 %) — pensez à acheter un pack Crédits INVEST.'}</span>
        </div>
      )}
      {(warning || reached) && (
        <div className="flex gap-2 flex-wrap mb-3">
          {data.packs.map((p) => (
            <button key={p.key} type="button" onClick={() => buyPack(p.key)} data-testid={`buy-pack-${p.key}`}
              className="px-3 py-2 rounded-xl text-xs font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">
              {p.label}
            </button>
          ))}
        </div>
      )}
      <details className="text-xs text-white/60">
        <summary className="cursor-pointer text-[#E9CF8E] font-semibold" data-testid="invest-history-toggle">Historique de consommation ({data.history.length})</summary>
        <div className="mt-2 max-h-44 overflow-y-auto space-y-1" data-testid="invest-history">
          {data.history.map((h) => (
            <div key={h.id} className="flex items-center gap-2">
              <span className="w-28 shrink-0 font-mono text-white/35">{new Date(h.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
              <span className="flex-1 truncate">{h.label}</span>
              <span className={`font-mono ${h.amount_uc < 0 ? 'text-red-300' : 'text-[#8CC63E]'}`}>{h.amount_uc > 0 ? '+' : ''}{h.amount_uc.toLocaleString('fr-FR')} uc</span>
            </div>
          ))}
        </div>
      </details>
      <button type="button" onClick={exportFinancings} data-testid="export-financings-pdf"
        className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
        <FileDown className="w-3.5 h-3.5" /> Export PDF de mes financements
      </button>
    </div>
  );
};
