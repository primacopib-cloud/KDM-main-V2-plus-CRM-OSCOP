import { useRef, useState } from 'react';
import { PenLine, Loader2, Thermometer, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';

const OUTCOMES = [
  ['LIVRE_CONFORME', 'Livré conforme'],
  ['LIVRE_AVEC_RESERVES', 'Livré avec réserves'],
  ['PARTIEL', 'Livraison partielle'],
  ['REFUSE_LIVRAISON', 'Refusé à la livraison'],
];

export const TransportEpodForm = ({ ot, onDone, onCancel }) => {
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ outcome: 'LIVRE_CONFORME', reserves: '', name: '', quality: '' });
  const [tempFile, setTempFile] = useState(null);
  const fileRef = useRef(null);
  const inp = 'w-full h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white placeholder:text-white/35';
  const needsReserves = form.outcome !== 'LIVRE_CONFORME';

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) { toast.error('Fichier trop volumineux (5 Mo max)'); return; }
    const reader = new FileReader();
    reader.onload = () => setTempFile({
      name: f.name, mime: f.type || 'application/octet-stream',
      b64: String(reader.result).split(',')[1],
    });
    reader.readAsDataURL(f);
  };

  const submit = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/logiscop-transport/orders/${ot.id}/epod`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
        body: JSON.stringify({
          ...form,
          temperature_file_b64: tempFile?.b64 || null,
          temperature_file_name: tempFile?.name || null,
          temperature_file_mime: tempFile?.mime || null,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Clôture impossible');
      toast.success(`OT ${ot.ref} clôturé — ${OUTCOMES.find(([k]) => k === form.outcome)?.[1]}. Archivage GEDESS en cours.`);
      onDone();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  return (
    <div className="rounded-lg p-3 my-1 bg-white/[0.04] border border-[#D9B35A]/30" data-testid={`epod-form-${ot.id}`}>
      <p className="text-[11px] font-bold text-[#E9CF8E] mb-2">Clôture ePOD — {ot.ref}</p>
      <div className="grid sm:grid-cols-3 gap-2 mb-2">
        <select className={inp} value={form.outcome} data-testid="epod-outcome"
          onChange={(e) => setForm({ ...form, outcome: e.target.value })}>
          {OUTCOMES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input className={inp} placeholder="Nom du signataire (destinataire) *" value={form.name}
          data-testid="epod-name" onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className={inp} placeholder="Qualité *" value={form.quality}
          data-testid="epod-quality" onChange={(e) => setForm({ ...form, quality: e.target.value })} />
      </div>
      <textarea className={`${inp} h-14 py-2`} data-testid="epod-reserves"
        placeholder={needsReserves ? 'Réserves précises et motivées (obligatoires) *' : 'Réserves (aucune si conforme)'}
        value={form.reserves} onChange={(e) => setForm({ ...form, reserves: e.target.value })} />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input ref={fileRef} type="file" className="hidden" data-testid="epod-temp-file-input"
          accept=".pdf,.csv,.xlsx,.png,.jpg,.jpeg" onChange={pickFile} />
        {tempFile ? (
          <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] bg-[#60A5FA]/15 text-[#93C5FD]"
            data-testid="epod-temp-file-chip">
            <Thermometer size={11} /> {tempFile.name}
            <button type="button" onClick={() => { setTempFile(null); if (fileRef.current) fileRef.current.value = ''; }}
              className="text-white/50 hover:text-red-300"><X size={11} /></button>
          </span>
        ) : (
          <button type="button" onClick={() => fileRef.current?.click()} data-testid="epod-temp-file-btn"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-bold bg-white/[0.06] text-white/60 hover:text-[#93C5FD] border border-white/15">
            <Thermometer size={11} /> Joindre le relevé de température {ot.temperature ? `(consigne ${ot.temperature})` : '(optionnel)'}
          </button>
        )}
      </div>
      <div className="mt-2 flex gap-2">
        <button type="button" onClick={submit} data-testid="epod-submit-btn"
          disabled={busy || form.name.length < 2 || form.quality.length < 2 || (needsReserves && form.reserves.length < 3)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-[#D9B35A] text-[#1F0A33] hover:bg-[#c9a34a] disabled:opacity-50">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <PenLine size={12} />} Signer l'ePOD
        </button>
        <button type="button" onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-[11px] text-white/50 hover:text-white border border-white/15">Annuler</button>
      </div>
    </div>
  );
};
