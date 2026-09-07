import { useEffect, useState } from 'react';
import { MapPin, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Switch } from '../ui/switch';

const inputCls = 'h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-xs text-white w-full';

const PointRow = ({ point }) => {
  const [f, setF] = useState({
    contact_email: point.contact_email || '',
    contact_phone: point.contact_phone || '',
    opening_hours: point.opening_hours || '',
    offers_drive: !!point.offers_drive,
    offers_delivery: !!point.offers_delivery,
    delivery_conditions: point.delivery_conditions || '',
  });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/lolodrive/admin/lolo-points/${point.id}`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(f),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Mise à jour échouée'); return; }
      toast.success(`${point.name} mis à jour ✓`);
    } catch { toast.error('Erreur de connexion'); } finally { setBusy(false); }
  };

  return (
    <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.07] space-y-2"
      data-testid={`relay-admin-row-${point.code}`}>
      <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr_1fr_1fr_auto_auto] gap-2 items-center">
      <div className="min-w-0">
        <p className="text-xs font-semibold text-white truncate">{point.name}</p>
        <p className="text-[10px] text-white/40 font-mono">{point.code} · {point.territory}</p>
      </div>
      <input value={f.contact_email} onChange={(e) => setF({ ...f, contact_email: e.target.value })}
        placeholder="Email de contact" className={inputCls} data-testid={`relay-email-${point.code}`} />
      <input value={f.contact_phone} onChange={(e) => setF({ ...f, contact_phone: e.target.value })}
        placeholder="Téléphone" className={inputCls} data-testid={`relay-phone-${point.code}`} />
      <input value={f.opening_hours} onChange={(e) => setF({ ...f, opening_hours: e.target.value })}
        placeholder="Horaires (ex: Lun–Sam 8h–19h)" className={inputCls} data-testid={`relay-hours-${point.code}`} />
      <div className="flex items-center gap-3 text-[10px] text-white/60">
        <label className="flex items-center gap-1.5">
          <Switch checked={f.offers_drive} onCheckedChange={(v) => setF({ ...f, offers_drive: v })}
            data-testid={`relay-drive-${point.code}`} /> Drive
        </label>
        <label className="flex items-center gap-1.5">
          <Switch checked={f.offers_delivery} onCheckedChange={(v) => setF({ ...f, offers_delivery: v })}
            data-testid={`relay-delivery-${point.code}`} /> Livraison
        </label>
      </div>
      <button type="button" onClick={save} disabled={busy} data-testid={`relay-save-${point.code}`}
        className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg text-[11px] font-bold text-black disabled:opacity-50"
        style={{ background: '#D9B35A' }}>
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Enregistrer
      </button>
      </div>
      <input value={f.delivery_conditions} onChange={(e) => setF({ ...f, delivery_conditions: e.target.value })}
        placeholder="Conditions de livraison (délais, frais, zone couverte…)"
        className={inputCls} data-testid={`relay-conditions-${point.code}`} />
    </div>
  );
};

export const LoloPointsContactPanel = () => {
  const [points, setPoints] = useState([]);
  const [nf, setNf] = useState({ name: '', code: '', territory: 'GP', city: '', address: '' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetch(`${API}/lolodrive/lolo-points`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { points: [] }))
      .then((d) => setPoints(d.points || []))
      .catch(() => {});
  }, []);

  const createPoint = async () => {
    if (nf.name.trim().length < 3) return toast.error('Nom du point relais requis (3 caractères min.)');
    setCreating(true);
    try {
      const code = nf.code.trim() || `LP-${nf.name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '-').slice(0, 12)}`;
      const r = await fetch(`${API}/lolodrive/admin/lolo-points`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ ...nf, code, city: nf.city || null, address: nf.address || null }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Création impossible');
      setPoints((prev) => [d, ...prev]);
      setNf({ name: '', code: '', territory: 'GP', city: '', address: '' });
      toast.success(`Point relais « ${d.name} » créé (${d.code})`);
    } catch (e) { toast.error(e.message); }
    finally { setCreating(false); }
  };
  const inCls = 'h-9 px-2.5 rounded-lg bg-white/[0.06] border border-white/15 text-white text-xs w-full placeholder:text-white/35';

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4" data-testid="relay-contact-panel">
      <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
        <MapPin className="w-4 h-4 text-[#D9B35A]" /> Fiches relais LOLODRIVE — coordonnées & services
      </h3>
      <p className="text-[11px] text-white/40 mb-3">
        Email, téléphone, horaires et services (Drive/Livraison) affichés aux titulaires du PASS dans leur espace.
      </p>
      <div className="rounded-xl p-3 mb-3 bg-[#8CC63E]/[0.06] border border-[#8CC63E]/30" data-testid="create-relay-form">
        <p className="text-[11px] font-bold text-[#8CC63E] m-0 mb-2">➕ Créer un point relais LOLODRIVE</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <input value={nf.name} onChange={(e) => setNf({ ...nf, name: e.target.value })} placeholder="Nom du point relais *" className={inCls} data-testid="new-relay-name" />
          <input value={nf.code} onChange={(e) => setNf({ ...nf, code: e.target.value })} placeholder="Code (auto si vide)" className={inCls} data-testid="new-relay-code" />
          <select value={nf.territory} onChange={(e) => setNf({ ...nf, territory: e.target.value })} className={`${inCls} bg-[#241243]`} data-testid="new-relay-territory">
            <option value="GP">Guadeloupe</option><option value="MQ">Martinique</option>
            <option value="GF">Guyane</option><option value="RE">La Réunion</option><option value="YT">Mayotte</option>
          </select>
          <input value={nf.city} onChange={(e) => setNf({ ...nf, city: e.target.value })} placeholder="Ville" className={inCls} data-testid="new-relay-city" />
          <input value={nf.address} onChange={(e) => setNf({ ...nf, address: e.target.value })} placeholder="Adresse" className={inCls} data-testid="new-relay-address" />
        </div>
        <button type="button" onClick={createPoint} disabled={creating} data-testid="new-relay-submit"
          className="mt-2 px-4 h-9 rounded-lg text-xs font-bold text-[#1F2A12] bg-[#8CC63E] hover:brightness-110 disabled:opacity-60 transition-[filter]">
          {creating ? 'Création…' : 'Créer le point relais'}
        </button>
      </div>
      <div className="space-y-2">
        {points.map((p) => <PointRow key={p.id} point={p} />)}
        {points.length === 0 && <p className="text-xs text-white/40">Aucun relais actif.</p>}
      </div>
    </div>
  );
};
