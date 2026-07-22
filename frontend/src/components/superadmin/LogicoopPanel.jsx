import { useCallback, useEffect, useState } from 'react';
import { Truck, Plus, Trash2, Power } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const ZoneChips = ({ zones, selected, onToggle, testPrefix }) => (
  <div className="flex flex-wrap gap-1">
    {zones.map((z) => {
      const on = selected.includes(z.code);
      return (
        <button key={z.code} type="button" onClick={() => onToggle(z.code)} data-testid={`${testPrefix}-${z.code}`}
          className={`px-2 py-0.5 rounded-lg text-[10px] font-bold border transition-colors ${on ? 'bg-[#D9B35A]/25 text-[#E9CF8E] border-[#D9B35A]/50' : 'bg-white/[0.04] text-white/40 border-white/10 hover:text-white/70'}`}>
          {z.code}
        </button>
      );
    })}
  </div>
);

export const LogicoopPanel = () => {
  const [ops, setOps] = useState([]);
  const [zones, setZones] = useState([]);
  const [form, setForm] = useState({ name: '', email: '', phone: '', exw_zones: [], cif_zones: [] });

  const load = useCallback(() => {
    fetch(`${API}/admin/logicoop/operators`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setOps(d.items || [])).catch(() => {});
    fetch(`${API}/admin/territories`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setZones(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleZone = (field, code) => setForm((f) => ({
    ...f, [field]: f[field].includes(code) ? f[field].filter((c) => c !== code) : [...f[field], code],
  }));

  const create = async () => {
    if (!form.name.trim() || !form.email.trim()) return toast.error('Nom et email requis');
    const r = await fetch(`${API}/admin/logicoop/operators`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Opérateur LOGICOOP « ${d.name} » créé`);
    setForm({ name: '', email: '', phone: '', exw_zones: [], cif_zones: [] });
    load();
  };

  const patchZones = async (op, field, code) => {
    const next = op[field].includes(code) ? op[field].filter((c) => c !== code) : [...op[field], code];
    const r = await fetch(`${API}/admin/logicoop/operators/${op.id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: next }),
    });
    if (!r.ok) return toast.error('Erreur');
    load();
  };

  const toggleActive = async (op) => {
    await fetch(`${API}/admin/logicoop/operators/${op.id}`, {
      method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !op.active }),
    });
    toast.success(op.active ? 'Opérateur désactivé' : 'Opérateur activé');
    load();
  };

  const remove = async (op) => {
    if (!window.confirm(`Supprimer l'opérateur « ${op.name} » ?`)) return;
    await fetch(`${API}/admin/logicoop/operators/${op.id}`, { method: 'DELETE', credentials: 'include' });
    toast.success('Opérateur supprimé');
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="logicoop-panel">
      <h3 className="font-display text-lg mb-1 text-white flex items-center gap-2">
        <Truck size={16} style={{ color: '#D9B35A' }} /> Opérateurs LOGICOOP
        <span className="text-sm font-normal text-white/50">({ops.length})</span>
      </h3>
      <p className="text-xs text-white/45 mb-4">Espace exclusif logistique : créez un opérateur (son email lui donne accès à /logicoop) et assignez ses zones d'entrepôt EXW et de livraison CIF.</p>

      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] mb-4 space-y-2">
        <div className="flex flex-wrap gap-2">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nom de l'opérateur" data-testid="logicoop-name-input" className={`${inp} flex-1 min-w-[160px]`} />
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email (compte d'accès)" data-testid="logicoop-email-input" className={`${inp} flex-1 min-w-[180px]`} />
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Téléphone" data-testid="logicoop-phone-input" className={`${inp} w-36`} />
        </div>
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <p className="text-[10px] font-bold text-white/50 uppercase mb-1">Zones entrepôt EXW</p>
            <ZoneChips zones={zones} selected={form.exw_zones} onToggle={(c) => toggleZone('exw_zones', c)} testPrefix="new-exw" />
          </div>
          <div className="flex-1 min-w-[200px]">
            <p className="text-[10px] font-bold text-white/50 uppercase mb-1">Zones livraison CIF</p>
            <ZoneChips zones={zones} selected={form.cif_zones} onToggle={(c) => toggleZone('cif_zones', c)} testPrefix="new-cif" />
          </div>
        </div>
        <button type="button" onClick={create} data-testid="logicoop-create-btn"
          className="btn-gold h-9 px-4 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5">
          <Plus size={14} /> Créer l'opérateur
        </button>
      </div>

      <div className="space-y-2">
        {ops.map((op) => (
          <div key={op.id} className={`p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] ${op.active ? '' : 'opacity-50'}`} data-testid={`logicoop-op-${op.id}`}>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <p className="text-sm font-bold text-white flex-1 min-w-[140px]">{op.name}</p>
              <span className="text-xs text-white/45">{op.email}{op.phone ? ` · ${op.phone}` : ''}</span>
              {!op.active && <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/60 uppercase">Désactivé</span>}
              <button type="button" onClick={() => toggleActive(op)} data-testid={`logicoop-toggle-${op.id}`} title={op.active ? 'Désactiver' : 'Activer'}
                className="p-1.5 rounded-lg bg-white/[0.06] border border-white/15 text-white/70 hover:text-white transition-colors"><Power size={13} /></button>
              <button type="button" onClick={() => remove(op)} data-testid={`logicoop-delete-${op.id}`}
                className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20 transition-colors"><Trash2 size={13} /></button>
            </div>
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <p className="text-[10px] font-bold text-white/50 uppercase mb-1">EXW ({op.exw_zones.length})</p>
                <ZoneChips zones={zones} selected={op.exw_zones} onToggle={(c) => patchZones(op, 'exw_zones', c)} testPrefix={`exw-${op.id}`} />
              </div>
              <div className="flex-1 min-w-[200px]">
                <p className="text-[10px] font-bold text-white/50 uppercase mb-1">CIF ({op.cif_zones.length})</p>
                <ZoneChips zones={zones} selected={op.cif_zones} onToggle={(c) => patchZones(op, 'cif_zones', c)} testPrefix={`cif-${op.id}`} />
              </div>
            </div>
          </div>
        ))}
        {!ops.length && <p className="text-sm text-white/45 py-3">Aucun opérateur LOGICOOP pour l'instant.</p>}
      </div>

      <RegisteredCarriers />
    </div>
  );
};

const RegisteredCarriers = () => {
  const [items, setItems] = useState(null);
  useEffect(() => {
    fetch(`${API}/admin/transportia/prospects`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setItems((d?.items || []).filter((p) => p.status === 'REGISTERED')))
      .catch(() => setItems([]));
  }, []);
  if (items === null) return null;
  return (
    <div className="mt-5 pt-4 border-t border-white/[0.08]" data-testid="logicoop-registered-carriers">
      <h4 className="text-sm font-semibold text-white flex items-center gap-2 mb-1">
        <Truck size={13} className="text-emerald-300" /> Transporteurs inscrits via TRANSPORT'IA
        <span className="text-xs font-normal text-white/50">({items.length})</span>
      </h4>
      <p className="text-[11px] text-white/40 mb-3">Prospects recrutés par l'agent TRANSPORT'IA dont l'inscription membre a été détectée — prêts à devenir opérateurs LOGICOOP.</p>
      {items.length === 0 ? (
        <p className="text-xs text-white/40 italic" data-testid="logicoop-registered-empty">Aucun transporteur inscrit pour le moment — la prospection continue via l'onglet Agents IA.</p>
      ) : (
        <div className="space-y-1.5">
          {items.map((p) => (
            <div key={p.id} className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20" data-testid={`logicoop-carrier-${p.id}`}>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300">Inscrit ✓</span>
              <p className="text-sm font-semibold text-white flex-1 min-w-[140px]">{p.company}
                <span className="text-white/40 font-normal text-xs"> · {p.territory}{p.fleet_type ? ` · ${p.fleet_type}` : ''}</span>
              </p>
              <span className="text-xs text-white/50">{p.contact_name ? `${p.contact_name} — ` : ''}{p.email}{p.phone ? ` · ${p.phone}` : ''}</span>
              {p.registered_at && <span className="text-[10px] text-white/35">le {new Date(p.registered_at).toLocaleDateString('fr-FR')}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
