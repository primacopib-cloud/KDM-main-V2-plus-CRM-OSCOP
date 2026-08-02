import { useEffect, useState } from 'react';
import { Truck } from 'lucide-react';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

// Taux de réserves par transporteur (litiges) — panel admin RàR
export const RarCarrierStats = () => {
  const [carriers, setCarriers] = useState([]);

  useEffect(() => {
    rarAPI.carrierStats().then((d) => setCarriers(d.carriers || [])).catch(() => {});
  }, []);

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
                <th className="text-right py-1.5 pl-2">Dont avoirs</th>
              </tr>
            </thead>
            <tbody>
              {carriers.map((c) => (
                <tr key={c.carrier} className="border-b border-white/[0.06]" data-testid={`rar-carrier-row-${c.carrier}`}>
                  <td className="py-1.5 pr-2 text-white font-bold">{c.carrier}</td>
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
                  <td className="py-1.5 pl-2 text-right text-sky-300 font-mono">{fmt(c.credited_cents)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
