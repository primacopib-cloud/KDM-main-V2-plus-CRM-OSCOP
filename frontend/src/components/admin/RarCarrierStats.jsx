import { useEffect, useState } from 'react';
import { Truck, Ban, RotateCcw, ScrollText, ChevronDown, ChevronUp, Download } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

// Taux de réserves par transporteur (litiges) — panel admin RàR
export const RarCarrierStats = () => {
  const [carriers, setCarriers] = useState([]);
  const [logOpen, setLogOpen] = useState(false);
  const [log, setLog] = useState(null);

  const load = () => {
    rarAPI.carrierStats().then((d) => setCarriers(d.carriers || [])).catch(() => {});
  };
  const loadLog = () => {
    rarAPI.carrierBlockLog().then((d) => setLog(d.entries || [])).catch(() => setLog([]));
  };
  useEffect(() => { load(); }, []);

  const toggleLog = () => {
    const next = !logOpen;
    setLogOpen(next);
    if (next && log === null) loadLog();
  };

  const toggleBlock = async (c) => {
    let reason = '';
    if (!c.blocked) {
      const r = window.prompt(`Motif de l'écartement de ${c.carrier} (affiché au survol) :`);
      if (r === null) return;
      reason = r.trim();
    }
    try {
      await rarAPI.setCarrierBlocked(c.carrier, !c.blocked, reason);
      toast.success(!c.blocked
        ? `${c.carrier} écarté — il ne sera plus proposé`
        : `${c.carrier} réintégré dans les propositions`);
      load();
      if (log !== null) loadLog();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-5" data-testid="rar-carrier-stats">
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2 flex items-center gap-1.5">
        <Truck className="w-3.5 h-3.5 text-[#4FD1A5]" /> Litiges par transporteur — taux de réserves
      </h4>
      {carriers.length === 0 ? (
        <p className="text-xs text-white/40">Aucune livraison confirmée pour le moment.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] uppercase text-white/40 border-b border-white/10">
                <th className="text-left py-1.5 pr-2">Transporteur</th>
                <th className="text-right py-1.5 px-2">Livraisons</th>
                <th className="text-right py-1.5 px-2">Avec réserves</th>
                <th className="text-right py-1.5 px-2">Taux de réserves</th>
                <th className="text-right py-1.5 px-2">Valeur contestée</th>
                <th className="text-right py-1.5 px-2">Dont avoirs</th>
                <th className="text-right py-1.5 pl-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {carriers.map((c) => (
                <tr key={c.carrier} className={`border-b border-white/[0.06] ${c.blocked ? 'opacity-60' : ''}`} data-testid={`rar-carrier-row-${c.carrier}`}>
                  <td className="py-1.5 pr-2 text-white font-bold">
                    {c.carrier}
                    {c.blocked && (
                      <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded-full text-red-300 bg-red-400/10 border border-red-400/30 font-normal cursor-help"
                        title={`${c.blocked_reason || 'Aucun motif renseigné'}${c.blocked_by ? ` — écarté par ${c.blocked_by}` : ''}${c.blocked_at ? ` le ${c.blocked_at.slice(0, 10)}` : ''}`}
                        data-testid={`rar-carrier-blocked-${c.carrier}`}>
                        Écarté
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 px-2 text-right text-white/70">{c.deliveries}</td>
                  <td className="py-1.5 px-2 text-right text-amber-300">{c.with_reserves}</td>
                  <td className="py-1.5 px-2 text-right">
                    <span className={`px-1.5 py-0.5 rounded font-mono font-bold ${
                      c.reserve_rate >= 50 ? 'text-red-300 bg-red-400/10'
                        : c.reserve_rate >= 20 ? 'text-amber-300 bg-amber-400/10'
                          : 'text-emerald-300 bg-emerald-400/10'}`}>
                      {c.reserve_rate.toLocaleString('fr-FR')} %
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-right text-white/70 font-mono">{fmt(c.disputed_cents)}</td>
                  <td className="py-1.5 px-2 text-right text-sky-300 font-mono">{fmt(c.credited_cents)}</td>
                  <td className="py-1.5 pl-2 text-right">
                    <button type="button" onClick={() => toggleBlock(c)} data-testid={`rar-carrier-block-${c.carrier}`}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ml-auto ${
                        c.blocked
                          ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30 hover:bg-emerald-400/20'
                          : 'text-red-300 bg-red-400/10 border-red-400/30 hover:bg-red-400/20'}`}>
                      {c.blocked ? <><RotateCcw className="w-3 h-3" /> Réintégrer</> : <><Ban className="w-3 h-3" /> Écarter</>}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-2 flex items-center gap-2">
        <button type="button" onClick={toggleLog} data-testid="rar-block-log-toggle"
          className="text-[10px] text-white/45 hover:text-white/70 flex items-center gap-1">
          <ScrollText className="w-3 h-3" /> Journal des écartements
          {logOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
        <button type="button" data-testid="rar-block-log-csv-btn"
          onClick={() => rarAPI.downloadBlockLogCsv().then(() => toast.success('Journal CSV téléchargé')).catch((e) => toast.error(e.message))}
          className="px-2 py-0.5 rounded text-[10px] font-bold text-white/55 border border-white/20 hover:text-white flex items-center gap-1">
          <Download className="w-3 h-3" /> CSV
        </button>
      </div>
      {logOpen && (
        <div className="mt-1.5 space-y-1 max-h-48 overflow-y-auto pr-1" data-testid="rar-block-log-list">
          {log && log.length === 0 && (
            <p className="text-[10px] text-white/35">Aucun écartement enregistré pour le moment.</p>
          )}
          {(log || []).map((e, i) => (
            <div key={i} className="flex flex-wrap items-center gap-1.5 p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.07] text-[10px]"
              data-testid={`rar-block-log-${i}`}>
              <span className="text-white/35">{(e.at || '').replace('T', ' ')}</span>
              <span className={`px-1.5 py-0.5 rounded-full font-bold border ${
                e.action === 'BLOCK'
                  ? 'text-red-300 bg-red-400/10 border-red-400/30'
                  : 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'}`}>
                {e.action === 'BLOCK' ? 'Écarté' : 'Réintégré'}
              </span>
              <b className="text-white">{e.carrier}</b>
              {e.reason && <span className="text-amber-200/70">— {e.reason}</span>}
              <span className="text-white/35 ml-auto">par {e.by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
