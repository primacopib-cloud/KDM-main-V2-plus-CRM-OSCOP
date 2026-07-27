import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Gift, Save, Loader2, Trophy } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { lolodriveAPI } from '../../services/api';

// Super admin : montant du bonus fidélité UC et seuil d'achats au comptoir
export const LoyaltyConfigPanel = () => {
  const [threshold, setThreshold] = useState('');
  const [bonus, setBonus] = useState('');
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [stats, setStats] = useState(null);

  useEffect(() => {
    lolodriveAPI.adminLoyaltyStats(month).then(setStats).catch(() => {});
  }, [month]);

  useEffect(() => {
    lolodriveAPI.adminLoyaltyConfig().then((c) => {
      setThreshold(String(c.threshold));
      setBonus(String(c.bonus_uc));
      setLoaded(true);
    }).catch(() => {});
  }, []);
  if (!loaded) return null;

  const save = async () => {
    setSaving(true);
    try {
      const r = await lolodriveAPI.adminUpdateLoyaltyConfig({
        threshold: parseInt(threshold, 10),
        bonus_uc: parseFloat(String(bonus).replace(',', '.')),
      });
      toast.success(`Fidélité mise à jour : +${r.bonus_uc} UC tous les ${r.threshold} achats ✓`);
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="loyalty-config-panel">
      <div className="font-semibold flex items-center gap-2 mb-3">
        <Gift className="w-4 h-4 text-[#D9B35A]" /> Programme fidélité comptoir
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-white/60">Tous les</span>
        <Input type="number" min="2" max="100" value={threshold} onChange={(e) => setThreshold(e.target.value)}
          className="bg-white/5 border-white/10 h-9 w-20 font-mono" data-testid="loyalty-threshold-input" />
        <span className="text-white/60">achats au comptoir, offrir</span>
        <Input type="number" min="0" value={bonus} onChange={(e) => setBonus(e.target.value)}
          className="bg-white/5 border-white/10 h-9 w-24 font-mono" data-testid="loyalty-bonus-input" />
        <span className="text-white/60">UC au client</span>
        <Button size="sm" onClick={save} disabled={saving} data-testid="loyalty-save-btn"
          className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <><Save className="w-3 h-3 mr-1" /> Enregistrer</>}
        </Button>
      </div>
      <p className="text-[11px] text-white/40 mt-2">
        Le bonus est crédité automatiquement sur le CREDI'SCOP du client identifié à la caisse, avec un reçu email 🎁.
      </p>
      <div className="mt-4 pt-4 border-t border-white/[0.06]">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <span className="text-sm font-semibold flex items-center gap-2">
            <Trophy className="w-3.5 h-3.5 text-[#D9B35A]" /> Bonus offerts par relais
          </span>
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="loyalty-stats-month"
            className="px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-white outline-none" />
          {stats && (
            <span className="ml-auto text-xs font-bold text-[#D9B35A]" data-testid="loyalty-stats-total">
              {stats.total_count} bonus · +{stats.total_uc} UC offerts
            </span>
          )}
        </div>
        {stats && stats.relays.length === 0 && (
          <p className="text-xs text-white/40" data-testid="loyalty-stats-empty">Aucun bonus fidélité offert sur ce mois.</p>
        )}
        {stats && stats.relays.map((r) => (
          <div key={r.point_code} className="flex items-center justify-between text-xs py-1.5 border-b border-white/[0.05]" data-testid={`loyalty-stats-${r.point_code}`}>
            <span>{r.point_name} <span className="text-white/35">({r.point_code})</span></span>
            <span className="font-mono">{r.count} bonus · <b className="text-[#D9B35A]">+{r.total_uc} UC</b>
              <span className="text-white/35"> ({(r.total_uc / 10).toFixed(2)} €)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
