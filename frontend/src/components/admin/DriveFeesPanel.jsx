import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Clock, Save, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';

// Super admin : tarifs UC de retrait Drive & livraison par catégorie et par créneau horaire
export const DriveFeesPanel = () => {
  const [cfg, setCfg] = useState(null);
  const [cats, setCats] = useState([]);
  const [kind, setKind] = useState('pickup');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    lolodriveAPI.feesConfig().then(setCfg).catch(() => {});
    lolodriveAPI.lolodriveCategories().then((d) => setCats((d.categories || []).map((c) => c.name))).catch(() => {});
  }, []);
  if (!cfg) return null;

  const slots = cfg[`${kind}_slots`] || [];
  const rates = cfg[`${kind}_rates`] || {};
  const rows = ['*', ...cats];

  const setSlot = (i, field, v) => {
    const next = { ...cfg, [`${kind}_slots`]: slots.map((s, j) => (j === i ? { ...s, [field]: v } : s)) };
    setCfg(next);
  };
  const setRate = (cat, sid, v) => {
    const next = { ...cfg, [`${kind}_rates`]: { ...rates, [cat]: { ...(rates[cat] || {}), [sid]: v } } };
    setCfg(next);
  };

  const save = async () => {
    setSaving(true);
    try {
      const clean = {};
      for (const [cat, bySlot] of Object.entries(cfg[`${kind}_rates`] || {})) {
        const entry = {};
        for (const [sid, r] of Object.entries(bySlot || {})) {
          const f = parseFloat(String(r).replace(',', '.'));
          if (!Number.isNaN(f) && f >= 0) entry[sid] = f;
        }
        if (Object.keys(entry).length) clean[cat] = entry;
      }
      await lolodriveAPI.adminUpdateFeesConfig({
        [`${kind}_slots`]: slots,
        [`${kind}_rates`]: clean,
        penalty_rates: Object.fromEntries(
          Object.entries(cfg.penalty_rates || { '*': 1 })
            .map(([c, r]) => [c, parseFloat(String(r).replace(',', '.'))])
            .filter(([, r]) => !Number.isNaN(r) && r >= 0)),
        no_pickup_block: cfg.no_pickup_block || { threshold: 3, window_days: 30, block_days: 15 },
        reliable_bonus: cfg.reliable_bonus || { bonus_uc: 10, min_orders: 5 },
        defective_alert_threshold: cfg.defective_alert_threshold ?? 3,
      });
      toast.success('Tarifs de créneaux enregistrés ✓');
      setCfg(await lolodriveAPI.feesConfig());
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="drive-fees-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="font-semibold flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#D9B35A]" /> Frais de retrait Drive & livraison (UC / article)
        </div>
        <div className="flex gap-2">
          {[['pickup', 'Retrait Drive'], ['delivery', 'Livraison']].map(([k, label]) => (
            <button key={k} type="button" onClick={() => setKind(k)} data-testid={`fees-kind-${k}`}
              className={`px-3 py-1 rounded-lg text-xs font-bold border ${kind === k ? 'text-[#D9B35A] bg-[#D9B35A]/15 border-[#D9B35A]/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
              {label}
            </button>
          ))}
          <Button size="sm" onClick={save} disabled={saving} data-testid="fees-save-btn"
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <><Save className="w-3 h-3 mr-1" /> Enregistrer</>}
          </Button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 gap-2 mb-3">
        {slots.map((s, i) => (
          <div key={s.id} className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-2.5 text-xs space-y-1.5" data-testid={`fees-slot-${s.id}`}>
            <input value={s.label} onChange={(e) => setSlot(i, 'label', e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-semibold" data-testid={`slot-label-${s.id}`} />
            <div className="flex items-center gap-1.5 text-white/50">
              De <input value={s.start || ''} onChange={(e) => setSlot(i, 'start', e.target.value)}
                className="w-16 bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-white font-mono" />
              à <input value={s.end || ''} onChange={(e) => setSlot(i, 'end', e.target.value)}
                className="w-16 bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-white font-mono" />
            </div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" data-testid="fees-rates-table">
          <thead>
            <tr className="text-white/40 uppercase text-[10px] tracking-wider">
              <td className="py-1.5 pr-2">Catégorie</td>
              {slots.map((s) => <td key={s.id} className="py-1.5 px-2">{s.label} (UC/article)</td>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((cat) => (
              <tr key={cat} className="border-t border-white/[0.05]">
                <td className="py-1.5 pr-2 font-semibold">{cat === '*' ? '★ Tarif par défaut (toutes catégories)' : cat}</td>
                {slots.map((s) => (
                  <td key={s.id} className="py-1.5 px-2">
                    <input type="text" data-testid={`rate-${cat === '*' ? 'default' : cat}-${s.id}`}
                      value={rates[cat]?.[s.id] ?? ''}
                      placeholder={cat === '*' ? '0' : `défaut ${rates['*']?.[s.id] ?? 0}`}
                      onChange={(e) => setRate(cat, s.id, e.target.value)}
                      className="w-24 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-white/40 mt-2">
        Frais facturés au client à la commande : tarif UC × nombre d'articles, selon la catégorie du produit et le créneau choisi.
        Laissez vide pour utiliser le tarif par défaut ★.
      </p>
      <div className="mt-4 pt-4 border-t border-white/[0.06]">
        <div className="text-sm font-semibold mb-2">⚠️ Pénalité de non-retrait <span className="text-white/40 font-normal text-xs">(UC / article, après la fin du créneau — 1 UC = 0,10 €)</span></div>
        <div className="flex flex-wrap gap-3">
          {['*', ...cats].map((cat) => (
            <label key={cat} className="flex items-center gap-1.5 text-xs">
              <span className={cat === '*' ? 'font-bold text-[#D9B35A]' : 'text-white/60'}>{cat === '*' ? '★ Défaut' : cat}</span>
              <input type="text" data-testid={`penalty-${cat === '*' ? 'default' : cat}`}
                value={cfg.penalty_rates?.[cat] ?? ''}
                placeholder={cat === '*' ? '1' : `déf. ${cfg.penalty_rates?.['*'] ?? 1}`}
                onChange={(e) => setCfg({ ...cfg, penalty_rates: { ...(cfg.penalty_rates || {}), [cat]: e.target.value } })}
                className="w-16 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            </label>
          ))}
        </div>
        <p className="text-[11px] text-white/40 mt-1.5">
          Le client est relancé automatiquement par email + SMS après son créneau, avec le montant de sa pénalité.
        </p>
        <div className="mt-4 pt-4 border-t border-white/[0.06]">
          <div className="text-sm font-semibold mb-2">🚫 Blocage des mauvais payeurs <span className="text-white/40 font-normal text-xs">(0 non-retraits = désactivé)</span></div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-white/60">
            Suspendre la commande Drive après
            <input type="text" data-testid="block-threshold-input"
              value={cfg.no_pickup_block?.threshold ?? 3}
              onChange={(e) => setCfg({ ...cfg, no_pickup_block: { ...(cfg.no_pickup_block || {}), threshold: e.target.value } })}
              className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            non-retrait(s) sur
            <input type="text" data-testid="block-window-input"
              value={cfg.no_pickup_block?.window_days ?? 30}
              onChange={(e) => setCfg({ ...cfg, no_pickup_block: { ...(cfg.no_pickup_block || {}), window_days: e.target.value } })}
              className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            jours, pendant
            <input type="text" data-testid="block-days-input"
              value={cfg.no_pickup_block?.block_days ?? 15}
              onChange={(e) => setCfg({ ...cfg, no_pickup_block: { ...(cfg.no_pickup_block || {}), block_days: e.target.value } })}
              className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            jours.
          </div>
          <p className="text-[11px] text-white/40 mt-1.5">
            Les pénalités remboursées (retrait tardif confirmé) ne comptent pas. Le blocage se lève automatiquement à l'échéance.
          </p>
        </div>
        <div className="mt-4 pt-4 border-t border-white/[0.06]">
          <div className="text-sm font-semibold mb-2">🏅 Bonus Client Fiable <span className="text-white/40 font-normal text-xs">(0 UC = désactivé — renouvelable tous les 6 mois)</span></div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-white/60">
            Offrir
            <input type="text" data-testid="reliable-bonus-input"
              value={cfg.reliable_bonus?.bonus_uc ?? 10}
              onChange={(e) => setCfg({ ...cfg, reliable_bonus: { ...(cfg.reliable_bonus || {}), bonus_uc: e.target.value } })}
              className="w-16 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            UC aux clients ayant retiré au moins
            <input type="text" data-testid="reliable-min-orders-input"
              value={cfg.reliable_bonus?.min_orders ?? 5}
              onChange={(e) => setCfg({ ...cfg, reliable_bonus: { ...(cfg.reliable_bonus || {}), min_orders: e.target.value } })}
              className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            commande(s) sur 6 mois sans aucun non-retrait.
          </div>
          <p className="text-[11px] text-white/40 mt-1.5">
            Le bonus est crédité automatiquement sur le CREDI'SCOP avec un email 🏅, et le badge s'affiche dans l'espace PASS du client.
          </p>
        </div>
        <div className="mt-4 pt-4 border-t border-white/[0.06]">
          <div className="text-sm font-semibold mb-2">⚠️ Alerte produit défectueux <span className="text-white/40 font-normal text-xs">(0 = désactivé)</span></div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-white/60">
            Alerter les super admins par email dès
            <input type="text" data-testid="defective-threshold-input"
              value={cfg.defective_alert_threshold ?? 3}
              onChange={(e) => setCfg({ ...cfg, defective_alert_threshold: e.target.value })}
              className="w-14 bg-white/5 border border-white/10 rounded px-2 py-1 text-white font-mono" />
            retour(s) « Défectueux » d'un même produit sur le mois.
          </div>
          <p className="text-[11px] text-white/40 mt-1.5">
            L'email indique la répartition par relais. Le retrait du produit se fait ensuite en un clic depuis « Fiches produits — TVA &amp; photos » ci-dessous.
          </p>
        </div>
      </div>
    </div>
  );
};
