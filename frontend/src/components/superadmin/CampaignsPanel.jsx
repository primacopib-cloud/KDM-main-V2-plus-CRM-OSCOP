import { useCallback, useEffect, useState } from 'react';
import { CalendarRange, Plus, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'h-8 rounded-lg px-2 text-[11px] text-white bg-white/[0.05] border border-white/15';
const toIso = (v) => (v ? new Date(v).toISOString() : '');

export const CampaignsPanel = ({ consultations, onChanged }) => {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(null);
  const attachable = (consultations || []).filter((c) => ['BROUILLON', 'EN_VALIDATION', 'VALIDEE'].includes(c.status));

  const load = useCallback(() => {
    fetch(`${API}/admin/campaigns`, opts()).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (path, body, ok) => {
    const r = await fetch(`${API}/admin/campaigns${path}`, body ? jsonOpts('POST', body) : { method: 'POST', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.message || ok);
    load();
    onChanged?.();
  };

  const create = async () => {
    if (!form.name || !form.opens_at || !form.closes_at) return toast.error('Nom et dates requis');
    const r = await fetch(`${API}/admin/campaigns`, jsonOpts('POST', { name: form.name, opens_at: toIso(form.opens_at), closes_at: toIso(form.closes_at) }));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Campagne « ${d.name} » créée`);
    setForm(null);
    load();
  };

  const publishAll = async (camp) => {
    const validated = (camp.lots || []).filter((l) => l.status === 'VALIDEE').length;
    if (!validated) return toast.info('Aucun lot au statut VALIDÉE dans cette campagne');
    if (!window.confirm(`Publier les ${validated} lot(s) validé(s) de « ${camp.name} » ?`)) return;
    const r = await fetch(`${API}/admin/campaigns/${camp.id}/publish-all`, { method: 'POST', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    const failed = (d.results || []).filter((x) => !x.ok);
    if (failed.length) toast.warning(`${d.published} publié(s) — échecs : ${failed.map((f) => `${f.ref} (${f.detail})`).join(' · ')}`, { duration: 9000 });
    else toast.success(`${d.published} lot(s) publié(s) en un clic`);
    load();
    onChanged?.();
  };

  const remove = async (camp) => {
    if (!window.confirm(`Supprimer la campagne « ${camp.name} » ? Les lots seront détachés (sans suppression).`)) return;
    await fetch(`${API}/admin/campaigns/${camp.id}`, { method: 'DELETE', ...opts() });
    load();
    onChanged?.();
  };

  return (
    <div className="glass-panel-soft rounded-[14px] p-4" data-testid="campaigns-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-white/70 uppercase flex items-center gap-1.5">
          <CalendarRange className="w-3.5 h-3.5" /> Campagnes multi-lots (calendrier commun)
        </h3>
        <button type="button" onClick={() => setForm(form ? null : { name: '', opens_at: '', closes_at: '' })} data-testid="campaign-create-btn"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-white/10 text-white/70 hover:text-white">
          {form ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />} {form ? 'Annuler' : 'Nouvelle campagne'}
        </button>
      </div>
      {form && (
        <div className="flex flex-wrap items-center gap-2 mb-3 p-2.5 rounded-xl bg-white/[0.04]">
          <input className={`${inp} flex-1 min-w-[160px]`} placeholder="Nom de la campagne" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="campaign-name-input" />
          <input className={inp} type="datetime-local" style={{ colorScheme: 'dark' }} value={form.opens_at}
            onChange={(e) => setForm({ ...form, opens_at: e.target.value })} data-testid="campaign-opens-input" />
          <input className={inp} type="datetime-local" style={{ colorScheme: 'dark' }} value={form.closes_at}
            onChange={(e) => setForm({ ...form, closes_at: e.target.value })} data-testid="campaign-closes-input" />
          <button type="button" onClick={create} className="px-3 py-1.5 rounded-lg text-[10.5px] font-bold"
            style={{ background: '#D9B35A', color: '#1F0A33' }} data-testid="campaign-save-btn">Créer</button>
        </div>
      )}
      {!items.length && <p className="text-xs text-white/40">Aucune campagne.</p>}
      <div className="space-y-2">
        {items.map((camp) => (
          <div key={camp.id} className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`campaign-row-${camp.id}`}>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-bold text-white/90 flex-1 min-w-[140px]">{camp.name}</span>
              <span className="text-white/45">{String(camp.opens_at).slice(0, 16).replace('T', ' ')} → {String(camp.closes_at).slice(0, 16).replace('T', ' ')}</span>
              <button type="button" onClick={() => publishAll(camp)} data-testid={`campaign-publish-${camp.id}`}
                className="px-2 py-1 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
                Publier les lots validés
              </button>
              <button type="button" onClick={() => act(`/${camp.id}/apply-calendar`, null, 'Calendrier ré-appliqué aux lots non publiés')}
                className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/10 text-white/60 hover:text-white" data-testid={`campaign-apply-${camp.id}`}>
                Appliquer le calendrier
              </button>
              <button type="button" onClick={() => remove(camp)} className="p-1 rounded bg-white/5 text-white/40 hover:text-red-400" data-testid={`campaign-delete-${camp.id}`}>
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
              {(camp.lots || []).map((l) => (
                <span key={l.id} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#D9B35A]/15 text-[#E9CF8E]">
                  {l.ref} · {l.status.replace(/_/g, ' ')}
                  <button type="button" onClick={() => act(`/${camp.id}/detach`, { consultation_id: l.id }, `${l.ref} détaché`)}
                    className="hover:text-red-400" title="Détacher" data-testid={`campaign-detach-${l.id}`}>×</button>
                </span>
              ))}
              {attachable.length > 0 && (
                <select className="h-6 rounded-lg px-1.5 text-[10px] text-white/70 bg-white/[0.05] border border-white/15" style={{ colorScheme: 'dark' }}
                  value="" onChange={(e) => e.target.value && act(`/${camp.id}/attach`, { consultation_id: e.target.value }, 'Lot rattaché')}
                  data-testid={`campaign-attach-${camp.id}`}>
                  <option value="" style={{ background: '#2A1045' }}>+ Rattacher un lot…</option>
                  {attachable.filter((c) => !(camp.lots || []).some((l) => l.id === c.id)).map((c) => (
                    <option key={c.id} value={c.id} style={{ background: '#2A1045' }}>{c.ref} — {c.title}</option>
                  ))}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
