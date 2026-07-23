import { useRef, useState } from 'react';
import { Scale, Paperclip, Download } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';
import { downloadTransportPdf } from './LogiscopSubscribeCard';

const STATUS_LABEL = { OPEN: ['Ouvert', '#F87171'], UNDER_REVIEW: ['En instruction', '#FBBF24'], RESOLVED: ['Résolu', '#7BC94E'] };
const RESP_LABEL = { INDETERMINEE: 'Indéterminée', TRANSPORTEUR: 'Transporteur', DONNEUR_ORDRE: 'Donneur d\'Ordre', PARTAGEE: 'Partagée' };

export const BuyerDisputesCard = ({ disputes, onChanged }) => {
  const fileRef = useRef(null);
  const [target, setTarget] = useState(null);

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    if (!f || !target) return;
    if (f.size > 8 * 1024 * 1024) { toast.error('Fichier trop volumineux (8 Mo max)'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const r = await fetch(`${API}/logiscop-transport/disputes/${target}/pieces`, {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
          body: JSON.stringify({ name: f.name, mime: f.type || 'application/octet-stream',
            content_b64: String(reader.result).split(',')[1] }),
        });
        if (!r.ok) throw new Error((await r.json()).detail || 'Ajout impossible');
        toast.success(`Pièce « ${f.name} » ajoutée au dossier`);
        onChanged?.();
      } catch (err) { toast.error(err.message); }
    };
    reader.readAsDataURL(f);
    e.target.value = '';
  };

  if (!disputes.length) return null;

  return (
    <div className="rounded-xl p-4 bg-red-500/[0.04] border border-red-500/20" data-testid="buyer-disputes-card">
      <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-2">
        <Scale className="w-4 h-4 text-red-300" /> Dossiers de litige ({disputes.length})
      </p>
      <input ref={fileRef} type="file" className="hidden" onChange={pickFile}
        accept=".pdf,.png,.jpg,.jpeg,.csv,.mp4,.mov" data-testid="dispute-piece-input" />
      <div className="space-y-2">
        {disputes.map((d) => {
          const [label, color] = STATUS_LABEL[d.status] || [d.status, '#999'];
          return (
            <div key={d.id} className="rounded-lg p-3 bg-white/[0.03] border border-white/[0.08] text-[11px]"
              data-testid={`dispute-${d.ref}`}>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="font-bold text-white">{d.ref}</span>
                <span className="text-white/50">OT {d.ot_ref} · Incident température (article 12)</span>
                <span className="font-bold" style={{ color }}>{label}</span>
                <span className="text-white/45">Responsabilité : <b className="text-white/70">{RESP_LABEL[d.responsibility]}</b></span>
                <button type="button" data-testid={`dispute-report-${d.ref}`}
                  onClick={() => downloadTransportPdf(`/logiscop-transport/disputes/${d.id}/report/pdf`,
                    `rapport-litige-${d.ref}.pdf`)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-[#93C5FD] hover:text-[#E9CF8E] border border-white/15">
                  <Download size={11} /> Rapport PDF
                </button>
                <button type="button" data-testid={`dispute-add-piece-${d.ref}`}
                  onClick={() => { setTarget(d.id); fileRef.current?.click(); }}
                  className="ml-auto inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/60 hover:text-[#E9CF8E] border border-white/15">
                  <Paperclip size={11} /> Ajouter une pièce
                </button>
              </div>
              {d.incident && (
                <p className="text-white/45">
                  {d.incident.violations_count} lecture(s) hors consigne {d.incident.consigne}±{d.incident.tolerance} °C
                  (min {d.incident.min} / max {d.incident.max} °C sur {d.incident.readings_count} lectures)
                </p>
              )}
              {d.resolution_note && <p className="text-white/60 mt-1">Résolution : {d.resolution_note}</p>}
              {(d.pieces || []).length > 0 && (
                <div className="mt-1 flex flex-wrap gap-2">
                  {d.pieces.map((p) => (
                    <button key={p.id} type="button"
                      onClick={() => downloadTransportPdf(`/logiscop-transport/disputes/pieces/${p.id}/download`, p.name)}
                      className="inline-flex items-center gap-1 text-[10px] text-[#93C5FD] hover:text-[#E9CF8E]">
                      <Download size={10} /> {p.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
