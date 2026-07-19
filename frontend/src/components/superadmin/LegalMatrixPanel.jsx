import { useCallback, useEffect, useState } from 'react';
import { Scale, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';

const STATUS_STYLE = {
  ROUGE: 'bg-red-500/15 text-red-400',
  ORANGE: 'bg-amber-500/15 text-amber-400',
  VERT: 'bg-[#7BC94E]/15 text-[#7BC94E]',
};
const STATUS_HELP = {
  ROUGE: 'Enchère inversée interdite — offres scellées uniquement',
  ORANGE: 'Validation juridique nominative requise avant publication',
  VERT: 'Enchère inversée ou offres scellées autorisées',
};

export const LegalMatrixPanel = ({ onChanged }) => {
  const [items, setItems] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [f, setF] = useState({ scope: 'category', category: '', sku_ean: '', status: 'ORANGE', legal_reason: '', legal_reference: 'Art. L.442-8 Code de commerce' });

  const load = useCallback(() => {
    fetch(`${API}/admin/legal-matrix?include_history=${showHistory}`, opts())
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, [showHistory]);
  useEffect(() => { load(); }, [load]);

  const classify = async () => {
    if (!f.category.trim() || !f.legal_reason.trim()) return toast.error('Catégorie et motif juridique requis');
    const r = await fetch(`${API}/admin/legal-matrix`, jsonOpts('POST', f));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Classification ${d.status} enregistrée (v${d.version})`);
    setF({ ...f, category: '', sku_ean: '', legal_reason: '' });
    load();
    onChanged?.();
  };

  return (
    <div className="glass-panel-soft rounded-[14px] p-4 space-y-3" data-testid="legal-matrix-panel">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-white/70 uppercase flex items-center gap-1.5">
          <Scale className="w-3.5 h-3.5 text-[#D9B35A]" /> Matrice juridique produit (L.442-8 — versionnée)
        </h3>
        <button type="button" onClick={() => setShowHistory(!showHistory)} className="text-[10px] text-white/50 hover:text-white underline">
          {showHistory ? 'Versions actives seulement' : 'Voir tout l’historique'}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select className={`${inp} w-28`} value={f.scope} onChange={(e) => setF({ ...f, scope: e.target.value })}>
          <option value="category">Catégorie</option>
          <option value="sku">SKU/EAN</option>
        </select>
        <input className={`${inp} w-40`} placeholder="Catégorie (ex : riz)" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} data-testid="matrix-category-input" />
        {f.scope === 'sku' && (
          <input className={`${inp} w-36`} placeholder="SKU / EAN" value={f.sku_ean} onChange={(e) => setF({ ...f, sku_ean: e.target.value })} />
        )}
        <select className={`${inp} w-28`} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })} data-testid="matrix-status-select" title={STATUS_HELP[f.status]}>
          <option value="ROUGE">ROUGE</option>
          <option value="ORANGE">ORANGE</option>
          <option value="VERT">VERT</option>
        </select>
        <input className={`${inp} flex-1 min-w-[180px]`} placeholder="Motif juridique (obligatoire)" value={f.legal_reason} onChange={(e) => setF({ ...f, legal_reason: e.target.value })} data-testid="matrix-reason-input" />
        <button type="button" onClick={classify} className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-[10.5px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }} data-testid="matrix-classify-btn">
          <Plus className="w-3 h-3" /> Classer
        </button>
      </div>
      <p className="text-[10px] text-white/40">{STATUS_HELP[f.status]}</p>
      <div className="space-y-1">
        {!items.length && <p className="text-xs text-white/40">Aucune classification. Toute catégorie non classée bloque la publication.</p>}
        {items.map((m) => (
          <div key={m.id} className={`flex flex-wrap items-center gap-2 text-xs py-1.5 border-b border-white/5 last:border-0 ${m.active ? '' : 'opacity-40'}`} data-testid={`matrix-row-${m.id}`}>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${STATUS_STYLE[m.status]}`}>{m.status}</span>
            <span className="font-semibold text-white/85">{m.category}{m.sku_ean ? ` · ${m.sku_ean}` : ''}</span>
            <span className="flex-1 text-white/50 truncate">{m.legal_reason} — {m.legal_reference}</span>
            <span className="text-white/35">v{m.version} · {m.author} · {String(m.validated_at).slice(0, 10)}{m.active ? '' : ' (remplacée)'}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
