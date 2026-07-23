import { useState } from 'react';
import { Plus, Trash2, Send, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';

const inp = 'w-full h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white placeholder:text-white/35';
const emptyGood = { designation: '', colis: '', poids_kg: '', volume_m3: '', palettes: '', valeur_eur: '', temperature: '' };
const emptyStop = { zone_code: '', address: '', date: '', slot: '', contact: '' };

const StopFields = ({ label, stop, setStop, zones, prefix }) => (
  <div className="rounded-lg p-3 bg-white/[0.03] border border-white/[0.08]">
    <p className="text-[11px] font-bold text-[#E9CF8E] mb-2">{label}</p>
    <div className="grid sm:grid-cols-2 gap-2">
      <select value={stop.zone_code} onChange={(e) => setStop({ ...stop, zone_code: e.target.value })}
        data-testid={`${prefix}-zone`} className={inp}>
        <option value="">Zone *</option>
        {zones.map((z) => <option key={z} value={z}>{z}</option>)}
      </select>
      <input className={inp} placeholder="Adresse complète *" value={stop.address} data-testid={`${prefix}-address`}
        onChange={(e) => setStop({ ...stop, address: e.target.value })} />
      <input className={inp} type="date" value={stop.date} data-testid={`${prefix}-date`}
        onChange={(e) => setStop({ ...stop, date: e.target.value })} />
      <input className={inp} placeholder="Créneau (ex. 08h-12h)" value={stop.slot}
        onChange={(e) => setStop({ ...stop, slot: e.target.value })} />
      <input className={`${inp} sm:col-span-2`} placeholder="Contact sur place (nom / téléphone)" value={stop.contact}
        onChange={(e) => setStop({ ...stop, contact: e.target.value })} />
    </div>
  </div>
);

export const TransportOrderForm = ({ zones, onCreated }) => {
  const [busy, setBusy] = useState(false);
  const [pickup, setPickup] = useState({ ...emptyStop });
  const [delivery, setDelivery] = useState({ ...emptyStop });
  const [goods, setGoods] = useState([{ ...emptyGood }]);
  const [extra, setExtra] = useState({ temperature: '', temperature_tolerance: '', pre_cooling: false, valeur_declaree_eur: '', notes: '' });

  const setGood = (i, field, value) => setGoods((g) => g.map((x, j) => (j === i ? { ...x, [field]: value } : x)));

  const submit = async () => {
    if (!pickup.zone_code || !delivery.zone_code || pickup.address.length < 4 || delivery.address.length < 4) {
      toast.error('Renseignez les zones et adresses d\'enlèvement et de livraison'); return;
    }
    if (!goods.some((g) => g.designation.length >= 2)) { toast.error('Ajoutez au moins une marchandise'); return; }
    setBusy(true);
    try {
      const num = (v) => (v === '' || v === null ? null : Number(v));
      const r = await fetch(`${API}/logiscop-transport/orders`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
        body: JSON.stringify({
          pickup, delivery, mode: 'route',
          goods: goods.filter((g) => g.designation.length >= 2).map((g) => ({
            designation: g.designation, colis: num(g.colis), poids_kg: num(g.poids_kg),
            volume_m3: num(g.volume_m3), palettes: num(g.palettes), valeur_eur: num(g.valeur_eur),
            temperature: g.temperature,
          })),
          temperature: extra.temperature, temperature_tolerance: extra.temperature_tolerance,
          pre_cooling: extra.pre_cooling, valeur_declaree_eur: num(extra.valeur_declaree_eur), notes: extra.notes,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Émission impossible');
      toast.success(`Ordre de Transport ${d.ref} émis — en attente de validation LOGI'SCOP`);
      setPickup({ ...emptyStop }); setDelivery({ ...emptyStop }); setGoods([{ ...emptyGood }]);
      setExtra({ temperature: '', temperature_tolerance: '', pre_cooling: false, valeur_declaree_eur: '', notes: '' });
      onCreated();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  return (
    <div className="rounded-xl p-4 bg-white/[0.03] border border-white/[0.08]" data-testid="transport-order-form">
      <p className="text-sm font-semibold text-white/85 mb-3">Émettre un Ordre de Transport nominatif (Mode D)</p>
      <div className="grid md:grid-cols-2 gap-3 mb-3">
        <StopFields label="Enlèvement (EXW)" stop={pickup} setStop={setPickup} zones={zones} prefix="ot-pickup" />
        <StopFields label="Livraison" stop={delivery} setStop={setDelivery} zones={zones} prefix="ot-delivery" />
      </div>
      <p className="text-[11px] font-bold text-[#E9CF8E] mb-1">Marchandises</p>
      {goods.map((g, i) => (
        <div key={i} className="grid grid-cols-2 sm:grid-cols-8 gap-1.5 mb-1.5 items-center">
          <input className={`${inp} col-span-2`} placeholder="Désignation / lot *" value={g.designation}
            data-testid={`ot-good-designation-${i}`} onChange={(e) => setGood(i, 'designation', e.target.value)} />
          <input className={inp} placeholder="Colis" type="number" value={g.colis} onChange={(e) => setGood(i, 'colis', e.target.value)} />
          <input className={inp} placeholder="Poids kg" type="number" value={g.poids_kg} onChange={(e) => setGood(i, 'poids_kg', e.target.value)} />
          <input className={inp} placeholder="Vol. m³" type="number" value={g.volume_m3} onChange={(e) => setGood(i, 'volume_m3', e.target.value)} />
          <input className={inp} placeholder="Palettes" type="number" value={g.palettes} onChange={(e) => setGood(i, 'palettes', e.target.value)} />
          <input className={inp} placeholder="Valeur €" type="number" value={g.valeur_eur} onChange={(e) => setGood(i, 'valeur_eur', e.target.value)} />
          <button type="button" onClick={() => setGoods((x) => x.filter((_, j) => j !== i))} disabled={goods.length === 1}
            className="text-red-300/70 hover:text-red-300 disabled:opacity-30 justify-self-center"><Trash2 size={14} /></button>
        </div>
      ))}
      <button type="button" onClick={() => setGoods((g) => [...g, { ...emptyGood }])} data-testid="ot-add-good-btn"
        className="inline-flex items-center gap-1 text-[11px] text-white/50 hover:text-[#E9CF8E] mb-3">
        <Plus size={12} /> Ajouter une ligne
      </button>
      <div className="grid sm:grid-cols-4 gap-2 mb-3">
        <input className={inp} placeholder="Température (ex. +4 °C)" value={extra.temperature}
          onChange={(e) => setExtra({ ...extra, temperature: e.target.value })} />
        <input className={inp} placeholder="Tolérance (ex. ±2 °C)" value={extra.temperature_tolerance}
          onChange={(e) => setExtra({ ...extra, temperature_tolerance: e.target.value })} />
        <input className={inp} placeholder="Valeur déclarée €" type="number" value={extra.valeur_declaree_eur}
          onChange={(e) => setExtra({ ...extra, valeur_declaree_eur: e.target.value })} />
        <label className="flex items-center gap-2 text-[11px] text-white/60 cursor-pointer">
          <input type="checkbox" checked={extra.pre_cooling} className="accent-[#D9B35A]"
            onChange={(e) => setExtra({ ...extra, pre_cooling: e.target.checked })} />
          Pré-refroidissement
        </label>
      </div>
      <textarea className={`${inp} h-16 py-2`} placeholder="Instructions particulières (accès, contraintes…)"
        value={extra.notes} onChange={(e) => setExtra({ ...extra, notes: e.target.value })} />
      <button type="button" onClick={submit} disabled={busy} data-testid="ot-submit-btn"
        className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-[#D9B35A] text-[#1F0A33] hover:bg-[#c9a34a] disabled:opacity-50">
        {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Émettre l'Ordre de Transport
      </button>
    </div>
  );
};
