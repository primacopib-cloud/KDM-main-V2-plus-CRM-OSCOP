import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, Clock, XCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function VerifyFinancingPage() {
  const { id } = useParams();
  const [doc, setDoc] = useState(undefined);

  useEffect(() => {
    fetch(`${API}/public/financing-contract/verify/${id}`)
      .then((r) => (r.ok ? r.json() : null)).then(setDoc).catch(() => setDoc(null));
  }, [id]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(160deg, #1F0A33 0%, #2A1045 100%)' }}
      data-testid="verify-financing-page">
      <div className="w-full max-w-[520px] rounded-2xl p-7 border border-[#D9B35A]/30 bg-white/[0.04]">
        <div className="flex items-center gap-3 mb-5">
          <ShieldCheck className="w-8 h-8 text-[#D9B35A]" />
          <div>
            <h1 className="text-lg font-bold text-white">Vérification de convention de financement</h1>
            <p className="text-xs text-white/50">O'SCOP — registre des conventions de financement ponctuel (eIDAS)</p>
          </div>
        </div>
        {doc === undefined && <p className="text-white/60 text-sm">Vérification en cours…</p>}
        {doc === null && (
          <div className="flex items-center gap-2 text-red-400 text-sm" data-testid="verify-fin-not-found">
            <XCircle size={16} /> Convention introuvable ou invalide.
          </div>
        )}
        {doc && (
          <div className="space-y-3" data-testid="verify-fin-result">
            <div className={`rounded-xl px-4 py-3 text-sm font-bold flex items-center gap-2 ${doc.fully_signed ? 'bg-[#7BC94E]/12 text-[#A5E27E] border border-[#7BC94E]/40' : 'bg-[#FBBF24]/10 text-[#FBBF24] border border-[#FBBF24]/40'}`}>
              {doc.fully_signed
                ? <><CheckCircle2 size={16} /> Convention authentique — signée par les deux parties</>
                : <><Clock size={16} /> Convention émise — en attente de signature(s)</>}
            </div>
            <dl className="text-sm space-y-1.5">
              {[['Référence', doc.reference],
                ['Objet du financement', doc.objet],
                ['Débiteur', doc.debiteur],
                ['Financeur', doc.financeur || '—']].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-b border-white/[0.06] pb-1">
                  <dt className="text-white/45">{k}</dt><dd className="text-white/90 text-right">{v}</dd>
                </div>
              ))}
            </dl>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-white/40 mb-1">Signatures électroniques</p>
              {[['Financeur', doc.signature_financeur], ["O'SCOP (Débiteur)", doc.signature_oscop]].map(([label, s]) => (
                <p key={label} className="text-xs text-white/75 flex items-center gap-1.5">
                  {s ? <CheckCircle2 size={11} className="text-[#7BC94E]" /> : <Clock size={11} className="text-[#FBBF24]" />}
                  <b>{label}</b>
                  {s ? ` — ${s.nom} · ${new Date(s.signed_at).toLocaleDateString('fr-FR')} · ${s.verification_code}` : ' — en attente'}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
