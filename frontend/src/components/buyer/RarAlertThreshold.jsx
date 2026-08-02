import { useEffect, useState } from 'react';
import { Bell, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

const fmtDate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');
const fmtEur = (c) => `${((c || 0) / 100).toLocaleString('fr-FR')} €`;

// Seuil d'alerte email — plafond RàR disponible
export const RarAlertThreshold = () => {
  const [value, setValue] = useState('');
  const [active, setActive] = useState(false);
  const [saved, setSaved] = useState(0);
  const [histOpen, setHistOpen] = useState(false);
  const [alerts, setAlerts] = useState(null);

  useEffect(() => {
    rarAPI.getAlertThreshold().then((d) => {
      setSaved(d.threshold_cents);
      setValue(d.threshold_cents ? String(d.threshold_cents / 100) : '');
      setActive(d.alert_active);
    }).catch(() => {});
  }, []);

  const save = async () => {
    const cents = Math.round(parseFloat(value || '0') * 100);
    try {
      await rarAPI.setAlertThreshold(cents);
      setSaved(cents);
      setActive(false);
      toast.success(cents > 0 ? `Alerte activée sous ${(cents / 100).toLocaleString('fr-FR')} €` : 'Alerte désactivée');
    } catch (e) { toast.error(e.message); }
  };

  const toggleHist = () => {
    const next = !histOpen;
    setHistOpen(next);
    if (next && alerts === null) {
      rarAPI.alertHistory().then((d) => setAlerts(d.alerts || [])).catch(() => setAlerts([]));
    }
  };

  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-1.5" data-testid="rar-alert-threshold">
      <span className="text-[10px] text-white/45 flex items-center gap-1">
        <Bell className="w-3 h-3" /> M'alerter par email si le plafond disponible passe sous
      </span>
      <input type="number" min="0" step="50" value={value} onChange={(e) => setValue(e.target.value)}
        placeholder="0 = off" data-testid="rar-alert-threshold-input"
        className="w-20 px-2 py-1 rounded bg-black/30 border border-white/15 text-[10px] text-white" />
      <span className="text-[10px] text-white/45">€</span>
      <button type="button" onClick={save} data-testid="rar-alert-threshold-save"
        className="px-2 py-1 rounded text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] flex items-center gap-1">
        <Check className="w-3 h-3" /> Enregistrer
      </button>
      {saved > 0 && active && (
        <span className="text-[9px] px-1.5 py-0.5 rounded-full text-amber-300 bg-amber-400/10 border border-amber-400/30" data-testid="rar-alert-active-badge">
          Alerte envoyée — plafond sous le seuil
        </span>
      )}
      </div>
      <button type="button" onClick={toggleHist} data-testid="rar-alert-history-toggle"
        className="mt-1.5 text-[10px] text-white/45 hover:text-white/70 flex items-center gap-1">
        <Bell className="w-3 h-3" /> Alertes envoyées
        {histOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {histOpen && (
        <div className="mt-1.5 space-y-1 max-h-40 overflow-y-auto pr-1" data-testid="rar-alert-history-list">
          {alerts && alerts.length === 0 && (
            <p className="text-[10px] text-white/35">Aucune alerte envoyée pour le moment.</p>
          )}
          {(alerts || []).map((a, i) => (
            <div key={i} className="flex items-center justify-between gap-2 p-1.5 rounded-lg bg-amber-400/[0.04] border border-amber-400/20 text-[10px]"
              data-testid={`rar-alert-history-${i}`}>
              <span className="text-white/60">
                <span className="text-white/35 mr-1.5">{fmtDate(a.sent_at)}</span>
                Plafond dispo <b className="text-amber-300">{fmtEur(a.available_cents)}</b> passé sous le seuil de <b>{fmtEur(a.threshold_cents)}</b>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
