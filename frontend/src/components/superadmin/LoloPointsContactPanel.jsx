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
    <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr_1fr_1fr_auto_auto] gap-2 items-center p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.07]"
      data-testid={`relay-admin-row-${point.code}`}>
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
  );
};

export const LoloPointsContactPanel = () => {
  const [points, setPoints] = useState([]);

  useEffect(() => {
    fetch(`${API}/lolodrive/lolo-points`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { points: [] }))
      .then((d) => setPoints(d.points || []))
      .catch(() => {});
  }, []);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4" data-testid="relay-contact-panel">
      <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
        <MapPin className="w-4 h-4 text-[#D9B35A]" /> Fiches relais LOLODRIVE — coordonnées & services
      </h3>
      <p className="text-[11px] text-white/40 mb-3">
        Email, téléphone, horaires et services (Drive/Livraison) affichés aux titulaires du PASS dans leur espace.
      </p>
      <div className="space-y-2">
        {points.map((p) => <PointRow key={p.id} point={p} />)}
        {points.length === 0 && <p className="text-xs text-white/40">Aucun relais actif.</p>}
      </div>
    </div>
  );
};
