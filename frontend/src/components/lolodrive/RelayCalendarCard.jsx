import { useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { SectionCard } from '../LolodriveLayout';

const DAY_LABELS = ['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'];

const DayChips = ({ values, onToggle, testPrefix }) => (
  <div className="flex flex-wrap gap-1.5">
    {DAY_LABELS.map((label, i) => {
      const on = values.includes(i);
      return (
        <button key={i} type="button" onClick={() => onToggle(i)} data-testid={`${testPrefix}-day-${i}`}
          className={`w-10 h-9 rounded-lg text-xs font-bold border transition-colors ${
            on ? 'bg-[#D9B35A] text-[#2A1045] on-gold border-[#D9B35A]'
               : 'bg-white/[0.04] text-white/55 border-white/15 hover:bg-white/10'}`}>
          {label}
        </button>
      );
    })}
  </div>
);

// Programmation des jours de retrait et de livraison du relais (visible dans le calendrier du panier)
export const RelayCalendarCard = ({ point, onSaved }) => {
  const [pickup, setPickup] = useState(point?.pickup_days || []);
  const [delivery, setDelivery] = useState(point?.delivery_days || []);
  const [busy, setBusy] = useState(false);

  const toggle = (list, setList) => (d) =>
    setList((v) => (v.includes(d) ? v.filter((x) => x !== d) : [...v, d].sort()));

  const save = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/lolodrive/manager/my-point/calendar`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include',
        body: JSON.stringify({ pickup_days: pickup, delivery_days: delivery }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Erreur ${res.status}`);
      toast.success('Calendrier du relais enregistré');
      onSaved?.();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionCard title={<span className="flex items-center gap-2"><CalendarDays className="w-4 h-4 text-[#D9B35A]" /> Calendrier du relais</span>}
      className="mb-6">
      <p className="text-xs text-white/50 mb-4">
        Programmez vos jours de retrait et de livraison : ils s'affichent dans le calendrier de créneau
        que les membres voient au panier. <b>Aucun jour coché = tous les jours ouverts.</b>
      </p>
      <div className="grid gap-4 sm:grid-cols-2" data-testid="relay-calendar-config">
        <div>
          <p className="text-xs font-bold text-[#E9CF8E] mb-2">Jours de retrait (Drive)</p>
          <DayChips values={pickup} onToggle={toggle(pickup, setPickup)} testPrefix="relay-pickup" />
        </div>
        <div>
          <p className="text-xs font-bold text-[#E9CF8E] mb-2">Jours de livraison</p>
          <DayChips values={delivery} onToggle={toggle(delivery, setDelivery)} testPrefix="relay-delivery" />
        </div>
      </div>
      <button type="button" onClick={save} disabled={busy} data-testid="relay-calendar-save"
        className="mt-4 px-4 py-2 rounded-lg text-xs font-bold text-[#2A1045] on-gold disabled:opacity-50 transition-transform hover:scale-[1.02]"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
        {busy ? 'Enregistrement…' : 'Enregistrer le calendrier'}
      </button>
    </SectionCard>
  );
};
