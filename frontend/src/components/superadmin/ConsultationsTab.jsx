import { useCallback, useEffect, useState } from 'react';
import { Gavel, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { LegalMatrixPanel } from './LegalMatrixPanel';
import { ConsultationTemplatesPanel } from './ConsultationTemplatesPanel';
import { EvaluationModal } from './EvaluationModal';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'w-full h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';

const S_STYLE = {
  BROUILLON: 'bg-white/10 text-white/60', EN_VALIDATION: 'bg-[#60A5FA]/15 text-[#60A5FA]',
  VALIDEE: 'bg-[#60A5FA]/15 text-[#60A5FA]', PUBLIEE: 'bg-[#7BC94E]/15 text-[#7BC94E]',
  INSCRIPTIONS_OUVERTES: 'bg-[#7BC94E]/15 text-[#7BC94E]', EN_COURS: 'bg-[#D9B35A]/20 text-[#E9CF8E]',
  CLOTUREE: 'bg-white/10 text-white/60', EN_EVALUATION: 'bg-[#60A5FA]/15 text-[#60A5FA]',
  ATTRIBUEE: 'bg-[#7BC94E]/15 text-[#7BC94E]', SANS_SUITE: 'bg-white/10 text-white/40',
  ANNULEE: 'bg-red-500/15 text-red-400', ARCHIVEE: 'bg-white/10 text-white/40',
};
const L_STYLE = { ROUGE: 'bg-red-500/15 text-red-400', ORANGE: 'bg-amber-500/15 text-amber-400', VERT: 'bg-[#7BC94E]/15 text-[#7BC94E]', NON_CLASSE: 'bg-white/10 text-white/50' };

const CreateModal = ({ onClose, onSaved }) => {
  const [f, setF] = useState({ title: '', type: 'STANDARD', procedure: 'SCELLEE', category: '', products: '', territories: 'GUADELOUPE', opens_at: '', closes_at: '', specs: '' });
  const save = async () => {
    if (!f.title || !f.category) return toast.error('Titre et catégorie requis');
    const body = {
      ...f,
      products: f.products.split('\n').filter(Boolean).map((l) => ({ label: l.trim() })),
      territories: f.territories.split(',').map((t) => t.trim()).filter(Boolean),
      opens_at: f.opens_at ? new Date(f.opens_at).toISOString() : null,
      closes_at: f.closes_at ? new Date(f.closes_at).toISOString() : null,
    };
    const r = await fetch(`${API}/admin/consultations`, jsonOpts('POST', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Consultation ${d.ref} créée (${d.legal_status} — ${d.procedure})`);
    onSaved();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="consultation-modal">
      <div className="w-full max-w-lg rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">Nouvelle consultation</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-2.5">
          <input className={inp} placeholder="Titre du lot" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} data-testid="cons-title-input" />
          <div className="grid grid-cols-2 gap-2">
            <select className={inp} value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}>
              <option value="STANDARD">Standard (20 CREDI'SCOP)</option>
              <option value="INTERTERRITORIALE">Interterritoriale (40 CREDI'SCOP)</option>
            </select>
            <select className={inp} value={f.procedure} onChange={(e) => setF({ ...f, procedure: e.target.value })} data-testid="cons-procedure-select">
              <option value="SCELLEE">Offres scellées</option>
              <option value="ENCHERE_INVERSEE">Enchère inversée</option>
            </select>
          </div>
          <input className={inp} placeholder="Catégorie (doit être classée dans la matrice)" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} data-testid="cons-category-input" />
          <textarea className={`${inp} h-16 py-2`} placeholder="Produits (un par ligne)" value={f.products} onChange={(e) => setF({ ...f, products: e.target.value })} />
          <input className={inp} placeholder="Territoires (séparés par des virgules)" value={f.territories} onChange={(e) => setF({ ...f, territories: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <div><p className="text-[10px] text-white/50 mb-1">Ouverture</p>
              <input type="datetime-local" className={inp} value={f.opens_at} onChange={(e) => setF({ ...f, opens_at: e.target.value })} style={{ colorScheme: 'dark' }} /></div>
            <div><p className="text-[10px] text-white/50 mb-1">Clôture (heure serveur, ferme)</p>
              <input type="datetime-local" className={inp} value={f.closes_at} onChange={(e) => setF({ ...f, closes_at: e.target.value })} style={{ colorScheme: 'dark' }} data-testid="cons-closes-input" /></div>
          </div>
          <textarea className={`${inp} h-16 py-2`} placeholder="Cahier des charges / spécifications" value={f.specs} onChange={(e) => setF({ ...f, specs: e.target.value })} />
          <p className="text-[10px] text-white/40">Critères par défaut : Prix 35 % · Qualité 20 % · Dispo 15 % · Logistique 15 % · Impact 10 % · Traçabilité 5 % (modifiables avant publication).</p>
          <button type="button" onClick={save} className="w-full py-2.5 rounded-xl text-xs font-bold" style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }} data-testid="cons-create-save-btn">
            Créer en brouillon
          </button>
        </div>
      </div>
    </div>
  );
};

export const ConsultationsTab = () => {
  const [items, setItems] = useState([]);
  const [modal, setModal] = useState(false);
  const [evalC, setEvalC] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/consultations`, opts()).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (url, body, okMsg) => {
    const r = await fetch(`${API}${url}`, body ? jsonOpts('POST', body) : { method: 'POST', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(okMsg || 'OK');
    load();
  };

  const validateOrange = (c) => {
    const reason = window.prompt('Motivation juridique de la validation ORANGE (obligatoire, nominative et tracée) :');
    if (!reason) return;
    const allowAuction = window.confirm('Autoriser l\'enchère inversée pour ce lot ? (Annuler = offres scellées)');
    act(`/admin/consultations/${c.id}/validate-orange`, { reason, allow_auction: allowAuction }, 'Lot ORANGE validé juridiquement');
  };
  const cancel = (c) => {
    const reason = window.prompt(`Motif d'annulation de ${c.ref} (les CREDI'SCOP des inscrits seront recrédités) :`);
    if (!reason) return;
    act(`/admin/consultations/${c.id}/transition`, { to: 'ANNULEE', reason }, 'Consultation annulée — CREDI\'SCOP recrédités');
  };

  const liquidity = async (c) => {
    const r = await fetch(`${API}/admin/consultations/${c.id}/liquidity`, opts());
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.info(`Score de liquidité — ${c.ref}`, {
      description: `${d.message}. Participants historiques de la catégorie : ${d.historical_participants}.`,
      duration: 9000,
    });
  };

  const buttons = (c) => {
    const B = ({ onClick, label, testid, gold }) => (
      <button type="button" onClick={onClick} data-testid={testid}
        className={`px-2.5 py-1.5 rounded-lg text-[10px] font-bold ${gold ? '' : 'bg-white/10 text-white/70 hover:text-white'}`}
        style={gold ? { background: '#D9B35A', color: '#1F0A33' } : {}}>{label}</button>
    );
    const out = [];
    if (['BROUILLON', 'EN_VALIDATION', 'VALIDEE'].includes(c.status)) out.push(<B key="lq" onClick={() => liquidity(c)} label="Score de liquidité" testid={`cons-liquidity-${c.id}`} />);
    if (c.status === 'BROUILLON') out.push(<B key="s" onClick={() => act(`/admin/consultations/${c.id}/transition`, { to: 'EN_VALIDATION' }, 'Soumise à validation')} label="Soumettre" testid={`cons-submit-${c.id}`} gold />);
    if (c.status === 'EN_VALIDATION') {
      if (!c.validations?.commercial) out.push(<B key="vc" onClick={() => act(`/admin/consultations/${c.id}/validate/commercial`, null, 'Validation commerciale OK')} label="Valider (KDMARCHE)" testid={`cons-val-com-${c.id}`} />);
      if (!c.validations?.platform) out.push(<B key="vp" onClick={() => act(`/admin/consultations/${c.id}/validate/platform`, null, 'Validation plateforme OK')} label="Valider (O'SCOP)" testid={`cons-val-plat-${c.id}`} />);
    }
    if (c.legal_status === 'ORANGE' && !c.orange_validation && !['ANNULEE', 'ARCHIVEE'].includes(c.status)) {
      out.push(<B key="vo" onClick={() => validateOrange(c)} label="Validation juridique ORANGE" testid={`cons-val-orange-${c.id}`} />);
    }
    if (c.status === 'VALIDEE') out.push(<B key="p" onClick={() => act(`/admin/consultations/${c.id}/publish`, null, 'Publiée — paramètres verrouillés')} label="Publier" testid={`cons-publish-${c.id}`} gold />);
    if (c.status === 'PUBLIEE') out.push(<B key="o" onClick={() => act(`/admin/consultations/${c.id}/transition`, { to: 'INSCRIPTIONS_OUVERTES' }, 'Inscriptions ouvertes')} label="Ouvrir inscriptions" testid={`cons-open-${c.id}`} gold />);
    if (c.status === 'INSCRIPTIONS_OUVERTES') out.push(<B key="r" onClick={() => act(`/admin/consultations/${c.id}/transition`, { to: 'EN_COURS' }, 'Consultation en cours')} label="Démarrer" gold />);
    if (c.status === 'EN_COURS') out.push(<B key="c" onClick={() => act(`/admin/consultations/${c.id}/transition`, { to: 'CLOTUREE' }, 'Clôturée')} label="Clôturer" />);
    if (c.status === 'CLOTUREE') out.push(<B key="e" onClick={() => act(`/admin/consultations/${c.id}/transition`, { to: 'EN_EVALUATION' }, 'En évaluation')} label="Évaluer" />);
    if (['CLOTUREE', 'EN_EVALUATION', 'ATTRIBUEE', 'SANS_SUITE', 'ARCHIVEE', 'ANNULEE'].includes(c.status)) {
      out.push(<B key="ev" onClick={() => setEvalC(c)} label={c.status === 'EN_EVALUATION' ? 'Scores & attribution' : 'Offres · PV · Exports'} testid={`cons-eval-${c.id}`} gold={c.status === 'EN_EVALUATION'} />);
    }
    if (['PUBLIEE', 'INSCRIPTIONS_OUVERTES', 'EN_COURS'].includes(c.status)) out.push(<B key="x" onClick={() => cancel(c)} label="Annuler" testid={`cons-cancel-${c.id}`} />);
    return out;
  };

  return (
    <div className="space-y-4" data-testid="consultations-tab">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Gavel className="w-4 h-4 text-[#D9B35A]" /> Consultations compétitives
        </h2>
        <button type="button" onClick={() => setModal(true)} data-testid="cons-create-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
          <Plus className="w-3.5 h-3.5" /> Nouvelle consultation
        </button>
      </div>

      <LegalMatrixPanel onChanged={load} />

      <ConsultationTemplatesPanel onCreated={load} />

      <div className="space-y-2">
        {!items.length && <p className="text-xs text-white/45">Aucune consultation.</p>}
        {items.map((c) => (
          <div key={c.id} className="glass-panel-soft rounded-[14px] p-3" data-testid={`cons-row-${c.id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-[#E9CF8E]">{c.ref}</span>
              <span className="text-sm font-bold text-white flex-1 min-w-[160px]">{c.title}</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${L_STYLE[c.legal_status]}`} data-testid={`cons-legal-${c.id}`}>{c.legal_status}</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/60">{c.procedure === 'SCELLEE' ? 'OFFRES SCELLÉES' : 'ENCHÈRE INVERSÉE'}</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${S_STYLE[c.status]}`} data-testid={`cons-status-${c.id}`}>{c.status.replace(/_/g, ' ')}</span>
            </div>
            <p className="text-[10px] text-white/40 mt-1">
              {c.type} · {c.cpc_cost} CREDI'SCOP · {(c.products || []).length} produit(s) · {(c.territories || []).join(', ')}
              {c.closes_at ? ` · clôture ${String(c.closes_at).slice(0, 16).replace('T', ' ')}` : ''}
              {c.orange_validation ? ` · ORANGE validé par ${c.orange_validation.author}` : ''}
              {c.published_snapshot_hash ? ` · hash ${c.published_snapshot_hash.slice(0, 12)}…` : ''}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2">{buttons(c)}</div>
          </div>
        ))}
      </div>
      {modal && <CreateModal onClose={() => setModal(false)} onSaved={() => { setModal(false); load(); }} />}
      {evalC && <EvaluationModal consultation={evalC} onClose={() => setEvalC(null)} onChanged={load} />}
    </div>
  );
};
