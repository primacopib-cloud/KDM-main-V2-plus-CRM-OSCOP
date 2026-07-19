import { useState } from 'react';
import { History, ChevronDown, ChevronUp } from 'lucide-react';

const REMINDER_LABELS = {
  activation: { label: "Email d'activation", color: '#7BC94E' },
  dunning: { label: 'Relance impayé', color: '#F87171' },
  warning: { label: 'Avertissement J+7', color: '#FBBF24' },
  suspended: { label: 'Suspension', color: '#F87171' },
  reactivated: { label: 'Réactivation', color: '#7BC94E' },
  sign_reminder: { label: 'Rappel signature', color: '#E9CF8E' },
  resume: { label: 'Relance abandon', color: '#60A5FA' },
  resume2: { label: 'Rappel final abandon (J+3)', color: '#60A5FA' },
};

const fmtDT = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—');

export const AdhesionReminders = ({ ob }) => {
  const [open, setOpen] = useState(false);
  const reminders = ob.reminders || [];
  if (!reminders.length) return null;
  return (
    <div className="w-full" data-testid={`adhesion-reminders-${ob.id}`}>
      <button type="button" onClick={() => setOpen(!open)}
        data-testid={`adhesion-reminders-toggle-${ob.id}`}
        className="inline-flex items-center gap-1 text-[10.5px] text-white/50 hover:text-white/80 transition-colors">
        <History className="w-3 h-3" /> {reminders.length} relance{reminders.length > 1 ? 's' : ''} envoyée{reminders.length > 1 ? 's' : ''}
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {[...reminders].reverse().map((r, i) => {
            const m = REMINDER_LABELS[r.type] || { label: r.type, color: '#9CA3AF' };
            return (
              <span key={`${r.type}-${r.at}-${i}`} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                style={{ color: m.color, background: `${m.color}18`, border: `1px solid ${m.color}45` }}>
                {m.label} · {fmtDT(r.at)}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};
