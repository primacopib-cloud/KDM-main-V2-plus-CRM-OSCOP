import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const STATUS_BADGE = {
  scheduled: { label: 'Programmé', bg: 'rgba(122,183,255,0.15)', color: '#7AB7FF' },
  notified: { label: 'Préavis envoyé', bg: 'rgba(217,179,90,0.15)', color: '#E9CF8E' },
  applied: { label: 'Appliqué', bg: 'rgba(154,255,122,0.15)', color: '#9CFF7A' },
  cancelled: { label: 'Annulé', bg: 'rgba(255,135,135,0.15)', color: '#FF8787' },
};

const frDate = (iso) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : '');

export const PriceSchedulePanel = ({ plans }) => {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ plan_id: '', new_price: '', effective_date: '' });

  const load = useCallback(() => {
    fetch(`${API}/admin/plans/price-schedule`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.plan_id) return toast.error('Choisissez une formule');
    const cents = Math.round(parseFloat(form.new_price) * 100);
    if (!cents || cents <= 0) return toast.error('Nouveau tarif invalide');
    if (!form.effective_date) return toast.error("Choisissez la date d'effet");
    const r = await fetch(`${API}/admin/plans/price-schedule`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: form.plan_id, new_price_cents: cents, effective_date: form.effective_date }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.status === 'notified'
      ? `Changement programmé — préavis déjà envoyé aux abonnés (effet ${frDate(d.effective_date)})`
      : `Changement programmé au ${frDate(d.effective_date)} — les abonnés seront prévenus 30 jours avant`);
    setForm({ plan_id: '', new_price: '', effective_date: '' });
    load();
  };

  const cancel = async (s) => {
    if (!window.confirm(`Annuler le changement de tarif de « ${s.plan_name} » prévu le ${frDate(s.effective_date)} ?`)) return;
    const r = await fetch(`${API}/admin/plans/price-schedule/${s.id}`, { method: 'DELETE', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Annulation impossible');
    toast.success('Programmation annulée');
    load();
  };

  return (
    <div className="rounded-2xl p-5 mt-6" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }} data-testid="price-schedule-panel">
      <h3 className="text-white font-bold flex items-center gap-2 mb-1">
        <CalendarClock className="w-4 h-4" style={{ color: '#D9B35A' }} /> Préavis tarifaire
      </h3>
      <p className="text-xs text-white/45 mb-4">
        Programmez un changement de prix à une date future : les membres abonnés sont informés par email 30 jours avant,
        puis le nouveau tarif s'applique automatiquement à la date d'effet.
      </p>

      <div className="flex flex-wrap gap-2 mb-5">
        <select value={form.plan_id} onChange={(e) => setForm({ ...form, plan_id: e.target.value })}
          data-testid="schedule-plan-select" className={`${inp} w-56`}>
          <option value="">— Formule —</option>
          {plans.map((p) => (
            <option key={p.id} value={p.id}>{p.name} (actuel : {((p.price_cents || 0) / 100).toFixed(0)} €)</option>
          ))}
        </select>
        <input type="number" min="1" step="0.01" value={form.new_price}
          onChange={(e) => setForm({ ...form, new_price: e.target.value })}
          placeholder="Nouveau tarif € HT/mois" data-testid="schedule-price-input" className={`${inp} w-48`} />
        <input type="date" value={form.effective_date}
          onChange={(e) => setForm({ ...form, effective_date: e.target.value })}
          data-testid="schedule-date-input" className={`${inp} w-44`} style={{ colorScheme: 'dark' }} />
        <button onClick={create} data-testid="schedule-create-btn"
          className="h-10 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5"
          style={{ background: '#D9B35A', color: '#070A10' }}>
          <Plus size={14} /> Programmer
        </button>
      </div>

      <div className="space-y-2">
        {items.map((s) => {
          const badge = STATUS_BADGE[s.status] || STATUS_BADGE.scheduled;
          return (
            <div key={s.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.04] border border-white/10 flex-wrap" data-testid={`schedule-row-${s.id}`}>
              <span className="text-sm text-white font-medium">{s.plan_name}</span>
              <span className="text-xs text-white/55">
                {((s.old_price_cents || 0) / 100).toFixed(0)} € → <strong className="text-white/85">{(s.new_price_cents / 100).toFixed(0)} €</strong> HT/mois
              </span>
              <span className="text-xs text-white/45">effet le {frDate(s.effective_date)}</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold" style={{ background: badge.bg, color: badge.color }}>
                {badge.label}{s.notice_sent_at && s.status === 'notified' ? ` le ${frDate(s.notice_sent_at)}` : ''}
              </span>
              <span className="text-[11px] text-white/35 ml-auto">{s.created_by}</span>
              {(s.status === 'scheduled' || s.status === 'notified') && (
                <button onClick={() => cancel(s)} title="Annuler" data-testid={`schedule-cancel-${s.id}`}
                  className="p-1.5 rounded-lg hover:bg-red-500/15 text-red-400"><Trash2 size={13} /></button>
              )}
            </div>
          );
        })}
        {!items.length && <p className="text-sm text-white/40 py-3 text-center">Aucun changement de tarif programmé.</p>}
      </div>
    </div>
  );
};
