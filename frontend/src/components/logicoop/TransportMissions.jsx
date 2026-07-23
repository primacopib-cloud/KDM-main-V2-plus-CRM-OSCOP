import { useEffect, useState } from 'react';
import { Truck } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

const STATUS = {
  ACCEPTE: ['À EXÉCUTER', 'bg-[#D9B35A]/20 text-[#E9CF8E]'],
  LIVRE_CONFORME: ['✓ LIVRÉ CONFORME', 'bg-emerald-500/15 text-emerald-400'],
  LIVRE_AVEC_RESERVES: ['LIVRÉ AVEC RÉSERVES', 'bg-amber-500/15 text-amber-400'],
  PARTIEL: ['PARTIEL', 'bg-fuchsia-500/15 text-fuchsia-300'],
};

export const TransportMissions = () => {
  const [items, setItems] = useState(null);

  useEffect(() => {
    fetch(`${API}/logicoop/transport-missions`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || [])).catch(() => setItems([]));
  }, []);

  if (!items) return null;

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mb-4" data-testid="logicoop-transport-missions">
      <h2 className="font-display text-lg text-white flex items-center gap-2 mb-1">
        <Truck className="w-4 h-4 text-[#D9B35A]" /> Missions Transport LOGI'SCOP ({items.length})
      </h2>
      <p className="text-xs text-white/45 mb-3">
        Ordres de Transport Mode D acceptés par LOGI'SCOP dans vos zones (enlèvement EXW / livraison CIF).
      </p>
      <div className="space-y-1.5">
        {items.map((m) => {
          const [label, cls] = STATUS[m.status] || [m.status, 'bg-white/10 text-white/60'];
          return (
            <div key={m.ot_id} className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs"
              data-testid={`transport-mission-${m.ot_id}`}>
              <div className="flex flex-wrap items-center gap-2">
                {m.missions.map((t) => (
                  <span key={t} className={`px-2 py-0.5 rounded-lg text-[9px] font-bold ${t === 'ENLEVEMENT' ? 'bg-[#D9B35A]/20 text-[#E9CF8E]' : 'bg-[#60A5FA]/20 text-[#60A5FA]'}`}>
                    {t === 'ENLEVEMENT' ? 'ENLÈVEMENT' : 'LIVRAISON'}
                  </span>
                ))}
                <span className="font-bold text-white">{m.ref}</span>
                <span className="text-white/50 flex-1 min-w-[120px]">{m.company_name}</span>
                <span className={`px-2 py-0.5 rounded-lg text-[9px] font-bold ${cls}`}>{label}</span>
                {m.price_ht_cents ? <span className="font-bold text-[#E9CF8E]">{eur(m.price_ht_cents)} HT</span> : null}
              </div>
              <p className="mt-1 text-white/50">
                <b className="text-white/70">Enlèvement :</b> {m.pickup?.address} ({m.pickup?.zone_code})
                {m.pickup?.date ? ` · ${m.pickup.date}${m.pickup.slot ? ' ' + m.pickup.slot : ''}` : ''}
                {m.pickup?.contact ? ` · ${m.pickup.contact}` : ''}
              </p>
              <p className="text-white/50">
                <b className="text-white/70">Livraison :</b> {m.delivery?.address} ({m.delivery?.zone_code})
                {m.delivery?.date ? ` · ${m.delivery.date}${m.delivery.slot ? ' ' + m.delivery.slot : ''}` : ''}
              </p>
              {m.goods_summary && <p className="text-white/40">Marchandises : {m.goods_summary}</p>}
            </div>
          );
        })}
        {!items.length && <p className="text-sm text-white/45">Aucun Ordre de Transport dans vos zones.</p>}
      </div>
    </div>
  );
};
