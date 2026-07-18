import { useState, useEffect, useCallback } from 'react';
import { Handshake, Loader2, Truck, Users2, Plus, Link2, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';

const CONV_STATUSES = [
  { value: 'RECUE', label: 'Reçue', cls: 'bg-amber-500/15 text-amber-700 border-amber-500/30' },
  { value: 'EN_NEGOCIATION', label: 'En négociation', cls: 'bg-blue-500/15 text-blue-700 border-blue-500/30' },
  { value: 'SIGNEE', label: 'Signée', cls: 'bg-green-500/15 text-green-700 border-green-500/30' },
  { value: 'RESILIEE', label: 'Résiliée', cls: 'bg-red-500/15 text-red-600 border-red-500/30' },
  { value: 'REFUSEE', label: 'Refusée', cls: 'bg-black/10 text-[#8A785F] border-black/15' },
];
const stCls = (s) => CONV_STATUSES.find((x) => x.value === s)?.cls || CONV_STATUSES[0].cls;
const stLabel = (s) => CONV_STATUSES.find((x) => x.value === s)?.label || s;

const TYPE_LABELS = { LOGISCOP: "Transporteur LOGI'SCOP", COOPER: 'COOPER', FOURNISSEUR: 'Fournisseur', RELAIS: 'Relais LOLODRIVE', AUTRE: 'Autre' };

const RequestCard = ({ req, onStatus }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-2xl bg-white border border-[#E9DCC0] overflow-hidden" data-testid={`convention-${req.reference}`}>
      <button onClick={() => setOpen(!open)} className="w-full p-4 flex items-center gap-3 text-left hover:bg-[#FBF6EC] transition-colors">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${stCls(req.status)}`}>{stLabel(req.status)}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[#3D2E1E] truncate">{req.structure_name} — {TYPE_LABELS[req.partner_type] || req.partner_type}</p>
          <p className="text-xs text-[#8A785F] truncate">{req.reference} · {req.territory} · {req.contact_name} &lt;{req.contact_email}&gt; · {new Date(req.created_at).toLocaleDateString('fr-FR')}</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-[#8A785F]" /> : <ChevronDown className="w-4 h-4 text-[#8A785F]" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          <div className="p-3 rounded-xl bg-[#F8F1E1] text-sm text-[#3D2E1E] whitespace-pre-wrap">{req.message}</div>
          {(req.history || []).length > 1 && (
            <div className="text-xs text-[#8A785F] space-y-1">
              {req.history.map((h, i) => (
                <p key={`${req.id}-h${i}`}>• {stLabel(h.action)} — {h.by} — {new Date(h.at).toLocaleString('fr-FR')}{h.note ? ` : ${h.note}` : ''}</p>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            {CONV_STATUSES.filter((s) => s.value !== req.status).map((s) => (
              <button key={s.value} onClick={() => onStatus(req.id, s.value)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${s.cls}`}
                data-testid={`convention-status-${req.reference}-${s.value}`}>
                → {s.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const CarriersPanel = () => {
  const [carriers, setCarriers] = useState([]);
  const [form, setForm] = useState({ name: '', territory: 'Guadeloupe', contact_email: '', contact_phone: '' });
  const load = useCallback(() => { apiCall('/cooper/carriers').then((d) => setCarriers(d.carriers)).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (form.name.length < 2) { toast.error('Nom du transporteur requis'); return; }
    try {
      await apiCall('/cooper/carriers', { method: 'POST', body: JSON.stringify(form) });
      toast.success('Transporteur LOGI\'SCOP ajouté');
      setForm({ name: '', territory: 'Guadeloupe', contact_email: '', contact_phone: '' });
      load();
    } catch (e) { toast.error(e.message || 'Erreur'); }
  };

  const toggle = async (c) => {
    try {
      await apiCall(`/cooper/carriers/${c.id}`, { method: 'PATCH', body: JSON.stringify({ is_active: !c.is_active }) });
      load();
    } catch (e) { toast.error(e.message || 'Erreur'); }
  };

  const inCls = 'h-9 px-3 rounded-xl border border-[#E9DCC0] bg-white text-xs';
  return (
    <div className="rounded-2xl bg-white border border-[#E9DCC0] p-5 space-y-3" data-testid="carriers-panel">
      <h3 className="font-semibold text-sm text-[#4C2A6E] flex items-center gap-2"><Truck className="w-4 h-4 text-[#D9B35A]" /> Transporteurs partenaires LOGI'SCOP</h3>
      <div className="flex flex-wrap gap-2 items-center">
        <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Nom du transporteur" className={inCls} data-testid="carrier-name-input" />
        <select value={form.territory} onChange={(e) => setForm((f) => ({ ...f, territory: e.target.value }))} className={inCls} data-testid="carrier-territory-select">
          {['Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Hexagone'].map((t) => <option key={t}>{t}</option>)}
        </select>
        <input value={form.contact_email} onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))} placeholder="Email contact" className={inCls} data-testid="carrier-email-input" />
        <input value={form.contact_phone} onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))} placeholder="Téléphone" className={inCls} data-testid="carrier-phone-input" />
        <button onClick={add} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-[#D9B35A]/20 text-[#B8860B] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/30" data-testid="carrier-add-btn">
          <Plus className="w-3.5 h-3.5" /> Ajouter
        </button>
      </div>
      {carriers.length === 0 ? (
        <p className="text-xs text-[#8A785F]">Aucun transporteur enregistré.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {carriers.map((c) => (
            <button key={c.id} onClick={() => toggle(c)} title="Cliquer pour activer/désactiver"
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-colors ${c.is_active ? 'bg-green-500/10 text-green-700 border-green-500/30' : 'bg-black/5 text-[#8A785F] border-black/10 line-through'}`}
              data-testid={`carrier-chip-${c.id}`}>
              <Truck className="w-3 h-3 inline mr-1" />{c.name} · {c.territory}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export const CoopersConventionsTab = () => {
  const [requests, setRequests] = useState(null);
  const [coopers, setCoopers] = useState([]);

  const load = useCallback(() => {
    apiCall('/partnership/admin/requests').then((d) => setRequests(d.requests)).catch(() => setRequests([]));
    apiCall('/partnership/admin/coopers').then((d) => setCoopers(d.coopers)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const setStatus = async (id, status) => {
    const note = window.prompt(`Note pour le passage à « ${stLabel(status)} » (optionnel) :`) || null;
    try {
      await apiCall(`/partnership/admin/requests/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status, note }) });
      toast.success(`Convention → ${stLabel(status)}`);
      load();
    } catch (e) { toast.error(e.message || 'Erreur'); }
  };

  const copyFormLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/partenariat`);
    toast.success('Lien du formulaire copié — à partager sur objectifscopoutremer & kdmarche');
  };

  return (
    <div className="space-y-5" data-testid="coopers-conventions-tab">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2 text-[#4C2A6E]">
          <Handshake className="w-5 h-5 text-[#D9B35A]" /> COOPER'S & Conventions de partenariat
        </h2>
        <button onClick={copyFormLink} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#D9B35A]/20 text-[#B8860B] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/30" data-testid="share-partnership-form-btn">
          <Link2 className="w-3.5 h-3.5" /> Copier le lien du formulaire /partenariat
        </button>
      </div>

      <div className="rounded-2xl bg-white border border-[#E9DCC0] p-5" data-testid="coopers-panel">
        <h3 className="font-semibold text-sm text-[#4C2A6E] flex items-center gap-2 mb-3"><Users2 className="w-4 h-4 text-[#D9B35A]" /> COOPER'S en poste ({coopers.length})</h3>
        {coopers.length === 0 ? (
          <p className="text-xs text-[#8A785F]">Aucun COOPER — attribuez le rôle via l'onglet « Droits & Rôles ».</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {coopers.map((c) => (
              <span key={c.id} className="px-3 py-1.5 rounded-xl text-xs bg-[#6FA82E]/10 text-[#4d7a1c] border border-[#6FA82E]/30" data-testid={`cooper-chip-${c.id}`}>
                {c.contact_name || c.email}{c.company_name ? ` · ${c.company_name}` : ''}
              </span>
            ))}
          </div>
        )}
      </div>

      <CarriersPanel />

      <div className="space-y-3">
        <h3 className="font-semibold text-sm text-[#4C2A6E]">Demandes de partenariat</h3>
        {requests === null ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>
        ) : requests.length === 0 ? (
          <div className="rounded-2xl bg-white border border-[#E9DCC0] p-8 text-center text-sm text-[#8A785F]" data-testid="conventions-empty">
            Aucune demande reçue — partagez le lien du formulaire /partenariat.
          </div>
        ) : (
          requests.map((r) => <RequestCard key={r.id} req={r} onStatus={setStatus} />)
        )}
      </div>
    </div>
  );
};
