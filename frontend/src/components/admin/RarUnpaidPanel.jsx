import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

const ageStyle = (d) => (d >= 14 ? 'text-red-300 bg-red-400/10' : d >= 7 ? 'text-amber-300 bg-amber-400/10' : 'text-emerald-300 bg-emerald-400/10');

// Tableau de bord des impayés RàR — ancienneté, relances, statut du plafond
export const RarUnpaidPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    rarAPI.adminUnpaid().then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  return (
    <div className="mt-5" data-testid="rar-unpaid-panel">
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2 flex items-center gap-1.5">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-300" /> Impayés RàR
        {data.count > 0 && (
          <span className="text-amber-300 normal-case tracking-normal" data-testid="rar-unpaid-total">
            — {data.count} commande{data.count > 1 ? 's' : ''} · {fmt(data.total_due_cents)} exigibles
          </span>
        )}
      </h4>
      {data.items.length === 0 ? (
        <p className="text-xs text-white/40" data-testid="rar-unpaid-empty">Aucun impayé — toutes les factures RàR sont encaissées. ✓</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] uppercase text-white/40 border-b border-white/10">
                <th className="text-left py-1.5 pr-2">Commande</th>
                <th className="text-left py-1.5 px-2">Organisation</th>
                <th className="text-right py-1.5 px-2">Exigible</th>
                <th className="text-right py-1.5 px-2">Ancienneté</th>
                <th className="text-right py-1.5 px-2">Relances</th>
                <th className="text-right py-1.5 pl-2">Plafond</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => (
                <tr key={i.order_number} className="border-b border-white/[0.06]" data-testid={`rar-unpaid-row-${i.order_number}`}>
                  <td className="py-1.5 pr-2 text-white font-bold">
                    {i.order_number}
                    {!i.delivered && <span className="ml-1.5 text-[9px] text-white/35 font-normal">(non livrée)</span>}
                  </td>
                  <td className="py-1.5 px-2 text-white/70">{i.org_name}</td>
                  <td className="py-1.5 px-2 text-right text-white font-mono">{fmt(i.due_cents)}</td>
                  <td className="py-1.5 px-2 text-right">
                    <span className={`px-1.5 py-0.5 rounded font-mono font-bold ${ageStyle(i.age_days || 0)}`}>
                      J+{i.age_days ?? '—'}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-right text-white/70">
                    {i.reminders}/3
                    {i.final_notice && (
                      <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded-full text-red-300 bg-red-400/10 border border-red-400/30"
                        title="Dernier rappel J+14 envoyé">
                        Dernier rappel ✓
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 pl-2 text-right">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold border ${
                      i.account_status === 'SUSPENDED'
                        ? 'text-red-300 bg-red-400/10 border-red-400/30'
                        : 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'}`}>
                      {i.account_status === 'SUSPENDED' ? 'Suspendu' : 'Actif'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-white/35 mt-1.5">
            Relances auto : J+3 puis toutes les 72 h (max 3) · Dernier rappel à J+14 avec alerte admin ·
            Suspension automatique du plafond 72 h après le dernier rappel sans encaissement.
          </p>
        </div>
      )}
    </div>
  );
};
