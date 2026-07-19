import { useCallback, useEffect, useState } from 'react';
import { X, Download, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const CRIT = ['qualite', 'disponibilite', 'logistique', 'impact', 'tracabilite'];
const inp = 'h-8 w-14 rounded px-1.5 text-[11px] text-white bg-white/[0.05] border border-white/15 text-center';

export const EvaluationModal = ({ consultation: c, onClose, onChanged }) => {
  const [entries, setEntries] = useState([]);
  const [scores, setScores] = useState({});
  const [ranking, setRanking] = useState(c._ranking || null);

  const load = useCallback(() => {
    fetch(`${API}/admin/consultations/${c.id}/bids`, opts())
      .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.detail); return d; })
      .then((d) => setEntries(d.entries || []))
      .catch((e) => toast.error(e.message));
  }, [c.id]);
  useEffect(() => { load(); }, [load]);

  const compute = async () => {
    const body = { scores: entries.map((e) => ({ entry_id: e.id, criteria: Object.fromEntries(CRIT.map((k) => [k, parseFloat(scores[`${e.id}:${k}`] || 0)])) })) };
    const r = await fetch(`${API}/admin/consultations/${c.id}/scores`, jsonOpts('POST', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setRanking(d.ranking);
    toast.success('Classement calculé (provisoire — validation requise)');
  };

  const doAward = async (entryId, isFirst) => {
    let reason = null;
    if (!isFirst) {
      reason = window.prompt('Attribution dérogatoire (≠ 1er du classement) — motivation écrite obligatoire :');
      if (!reason) return;
    }
    const r = await fetch(`${API}/admin/consultations/${c.id}/award`, jsonOpts('POST', { entry_id: entryId, derogation_reason: reason }));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Attribuée à ${d.winner} — projet d'Attestation nominative généré`);
    onChanged();
    onClose();
  };

  const dl = async (path, name) => {
    const r = await fetch(`${API}/admin/consultations/${c.id}/${path}`, opts());
    if (!r.ok) return toast.error('Export impossible');
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  };

  const sendAttestation = async () => {
    if (!window.confirm('Envoyer le projet d\'Attestation nominative (PDF) par email au fournisseur retenu ?')) return;
    const r = await fetch(`${API}/admin/consultations/${c.id}/attestation/send`, { method: 'POST', ...opts() });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Attestation envoyée à ${d.sent_to}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.8)' }} data-testid="evaluation-modal">
      <div className="w-full max-w-3xl rounded-[18px] p-5 max-h-[92vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white">Évaluation — {c.ref} · {c.title}</h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-[10px] text-white/45 mb-3">
          Le score prix est automatique (meilleure offre = 100). Notez chaque critère de 0 à 100 avec justificatifs.
          Départage déterministe : qualité → logistique → disponibilité → traçabilité → première offre horodatée.
        </p>
        {c.status === 'EN_EVALUATION' && (
          <div className="space-y-2 mb-4">
            {entries.map((e) => (
              <div key={e.id} className="glass-panel-soft rounded-xl p-3" data-testid={`eval-entry-${e.id}`}>
                <div className="flex items-center gap-2 text-xs text-white/85 font-semibold mb-1.5">
                  <span className="flex-1">{e.company}</span>
                  <span className="text-[#E9CF8E]">{e.bid?.amount_ht_cents ? `${eur(e.bid.amount_ht_cents)} HT` : 'Aucune offre'}</span>
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                  {CRIT.map((k) => (
                    <label key={k} className="text-[9.5px] text-white/50 flex flex-col gap-0.5">
                      {k}
                      <input className={inp} type="number" min="0" max="100" value={scores[`${e.id}:${k}`] ?? ''}
                        onChange={(ev) => setScores((s) => ({ ...s, [`${e.id}:${k}`]: ev.target.value }))}
                        data-testid={`eval-score-${e.id}-${k}`} />
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button type="button" onClick={compute} className="px-3 py-2 rounded-lg text-[11px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }} data-testid="eval-compute-btn">
              Calculer le classement
            </button>
          </div>
        )}
        {ranking && (
          <div className="space-y-1.5 mb-4">
            <h4 className="text-xs font-bold text-white/70 uppercase">Classement provisoire</h4>
            {ranking.map((r, i) => (
              <div key={r.entry_id} className="flex items-center gap-2 text-xs py-1.5 border-b border-white/5">
                <span className="w-8 font-bold text-[#E9CF8E]">#{i + 1}</span>
                <span className="flex-1 text-white/85">{r.company}</span>
                <span className="text-white/60">{eur(r.amount_ht_cents)} HT</span>
                <span className="font-bold text-white">{r.total.toFixed(2)}</span>
                {c.status === 'EN_EVALUATION' && (
                  <button type="button" onClick={() => doAward(r.entry_id, i === 0)} data-testid={`eval-award-${r.entry_id}`}
                    className={`px-2 py-1 rounded text-[10px] font-bold ${i === 0 ? '' : 'bg-white/10 text-white/60'}`}
                    style={i === 0 ? { background: '#7BC94E', color: '#1F0A33' } : {}}>
                    {i === 0 ? 'Attribuer' : 'Dérogation'}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          {['ATTRIBUEE', 'SANS_SUITE', 'ANNULEE', 'ARCHIVEE'].includes(c.status) && (
            <button type="button" onClick={() => dl('pv.pdf', `PV-${c.ref}.pdf`)} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }} data-testid="eval-pv-btn">
              <FileText className="w-3.5 h-3.5" /> Procès-verbal PDF
            </button>
          )}
          {['ATTRIBUEE', 'ARCHIVEE'].includes(c.status) && (
            <>
              <button type="button" onClick={() => dl('attestation.pdf', `Attestation-${c.ref}.pdf`)} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold" style={{ background: '#7BC94E', color: '#1F0A33' }} data-testid="eval-attestation-btn">
                <FileText className="w-3.5 h-3.5" /> Attestation nominative PDF
              </button>
              <button type="button" onClick={sendAttestation} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold bg-white/10 text-white/80" data-testid="eval-attestation-send-btn">
                Envoyer au fournisseur retenu
              </button>
            </>
          )}
          <button type="button" onClick={() => dl('export.csv', `${c.ref}-audit.csv`)} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold bg-white/10 text-white/70" data-testid="eval-csv-btn">
            <Download className="w-3.5 h-3.5" /> Journal CSV
          </button>
          <button type="button" onClick={() => dl('export.json', `${c.ref}-audit.json`)} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-bold bg-white/10 text-white/70" data-testid="eval-json-btn">
            <Download className="w-3.5 h-3.5" /> Journal JSON
          </button>
        </div>
      </div>
    </div>
  );
};
