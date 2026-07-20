import { useEffect, useState } from 'react';
import { Settings2, Save } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';
const sel = 'h-8 rounded-lg px-2 text-[11px] text-white bg-white/[0.05] border border-white/15';

const EVENT_LABELS = {
  referral_bonus: 'Bonus de parrainage crédité',
  referral_welcome: 'Bonus de bienvenue (filleul)',
  closure_reminder: 'Rappel de clôture (24h avant)',
  report_available: "Rapport d'analyse disponible",
};
const CHANNELS = [
  { value: 'both', label: 'Email + In-app' },
  { value: 'email', label: 'Email uniquement' },
  { value: 'inapp', label: 'In-app uniquement' },
  { value: 'none', label: 'Aucune' },
];
const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
const FREQS = [
  { value: 'weekly', label: 'Hebdomadaire' },
  { value: 'biweekly', label: 'Toutes les 2 semaines' },
  { value: 'monthly', label: 'Mensuel' },
];

export const VendorPreferencesPanel = () => {
  const [prefs, setPrefs] = useState(null);
  const [recap, setRecap] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/prefs/notifications`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setPrefs(d.prefs)).catch(() => {});
    fetch(`${API}/api/prefs/recap`, { credentials: 'include' })
      .then((r) => r.json()).then(setRecap).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const [r1, r2] = await Promise.all([
        fetch(`${API}/api/prefs/notifications`, {
          method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prefs }),
        }),
        fetch(`${API}/api/prefs/recap`, {
          method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(recap),
        }),
      ]);
      if (!r1.ok || !r2.ok) {
        const d = !r1.ok ? await r1.json() : await r2.json();
        toast.error(d.detail || 'Erreur lors de l\'enregistrement');
      } else {
        toast.success('Préférences enregistrées');
      }
    } finally {
      setSaving(false);
    }
  };

  if (!prefs || !recap) return null;

  return (
    <div className={`${panel} p-5`} data-testid="vendor-prefs-panel">
      <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
        <Settings2 className="w-4 h-4 text-[#D9B35A]" /> Préférences de notifications
      </h3>
      <p className="text-[11px] text-white/40 mb-4">Choisissez vos canaux par type d'événement et personnalisez votre récapitulatif périodique.</p>

      <div className="space-y-2 mb-5">
        {Object.keys(EVENT_LABELS).map((ev) => (
          <div key={ev} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="flex-1 min-w-[200px] text-white/75">{EVENT_LABELS[ev]}</span>
            <select className={sel} style={{ colorScheme: 'dark' }} value={prefs[ev] || 'both'}
              onChange={(e) => setPrefs({ ...prefs, [ev]: e.target.value })} data-testid={`pref-channel-${ev}`}>
              {CHANNELS.map((c) => <option key={c.value} value={c.value} style={{ background: '#2A1045' }}>{c.label}</option>)}
            </select>
          </div>
        ))}
      </div>

      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-white/85">Récapitulatif périodique par email</span>
          <label className="inline-flex items-center gap-2 cursor-pointer text-xs text-white/60">
            <input type="checkbox" checked={recap.enabled} data-testid="recap-enabled-toggle"
              onChange={(e) => setRecap({ ...recap, enabled: e.target.checked })}
              className="w-4 h-4 accent-[#D9B35A]" />
            {recap.enabled ? 'Activé' : 'Désactivé'}
          </label>
        </div>
        {recap.enabled && (
          <div className="flex flex-wrap items-center gap-2">
            <select className={sel} style={{ colorScheme: 'dark' }} value={recap.day} data-testid="recap-day-select"
              onChange={(e) => setRecap({ ...recap, day: Number(e.target.value) })}>
              {DAYS.map((d, i) => <option key={d} value={i} style={{ background: '#2A1045' }}>{d}</option>)}
            </select>
            <select className={sel} style={{ colorScheme: 'dark' }} value={recap.frequency} data-testid="recap-frequency-select"
              onChange={(e) => setRecap({ ...recap, frequency: e.target.value })}>
              {FREQS.map((f) => <option key={f.value} value={f.value} style={{ background: '#2A1045' }}>{f.label}</option>)}
            </select>
            <span className="text-[10px] text-white/40">Solde, consultations ouvertes et notifications non lues.</span>
          </div>
        )}
      </div>

      <button type="button" onClick={save} disabled={saving} data-testid="prefs-save-btn"
        className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold hover:brightness-110 transition-all disabled:opacity-50"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
        <Save className="w-3.5 h-3.5" /> {saving ? 'Enregistrement…' : 'Enregistrer mes préférences'}
      </button>
    </div>
  );
};
