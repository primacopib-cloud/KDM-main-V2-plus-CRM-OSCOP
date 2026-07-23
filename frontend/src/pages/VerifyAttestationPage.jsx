import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, Clock, XCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function VerifyAttestationPage() {
  const { id } = useParams();
  const [att, setAtt] = useState(undefined);

  useEffect(() => {
    fetch(`${API}/attestations/verify/${id}`)
      .then((r) => (r.ok ? r.json() : null)).then(setAtt).catch(() => setAtt(null));
  }, [id]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(160deg, #1F0A33 0%, #2A1045 100%)' }}
      data-testid="verify-attestation-page">
      <div className="w-full max-w-[520px] rounded-2xl p-7 border border-[#D9B35A]/30 bg-white/[0.04]">
        <div className="flex items-center gap-3 mb-5">
          <ShieldCheck className="w-8 h-8 text-[#D9B35A]" />
          <div>
            <h1 className="text-lg font-bold text-white">Vérification d'attestation</h1>
            <p className="text-xs text-white/50">KDMARCHÉ × O'SCOP — registre des attestations nominatives</p>
          </div>
        </div>
        {att === undefined && <p className="text-white/60 text-sm">Vérification en cours…</p>}
        {att === null && (
          <div className="flex items-center gap-2 text-red-400 text-sm" data-testid="verify-not-found">
            <XCircle size={16} /> Attestation introuvable ou invalide.
          </div>
        )}
        {att && (
          <div className="space-y-3" data-testid="verify-result">
            <div className={`rounded-xl px-4 py-3 text-sm font-bold flex items-center gap-2 ${att.status === 'signed' ? 'bg-[#7BC94E]/12 text-[#A5E27E] border border-[#7BC94E]/40' : att.status === 'closed' ? 'bg-[#60A5FA]/10 text-[#93C5FD] border border-[#60A5FA]/40' : 'bg-[#FBBF24]/10 text-[#FBBF24] border border-[#FBBF24]/40'}`}>
              {att.status === 'signed'
                ? <><CheckCircle2 size={16} /> Attestation authentique — signée par les trois parties</>
                : att.status === 'closed'
                  ? <><CheckCircle2 size={16} /> Attestation clôturée — RCR remboursée au Fournisseur</>
                  : <><Clock size={16} /> Attestation émise — en attente de contre-signature</>}
            </div>
            <dl className="text-sm space-y-1.5">
              {[['Référence', `${att.ref}${att.version ? ` / ${att.version}` : ''}`],
                ['Réf. FOGEDOM-RCR', att.fogedom_ref || '—'],
                ['Convention-cadre', att.convention_ref || '—'],
                ['Fournisseur', att.vendor_name],
                ['Produit', `${att.product_name} (${att.category})`],
                ['Territoire(s)', (att.zones || []).join(', ') || '—'],
                ["Volume d'Achat Ferme", `${att.volume} ${att.unit}(s)`],
                ["Montant d'Achat Ferme HT", `${(att.montant_agrege_cents / 100).toFixed(2)} €`],
                ['Taux RCR / Plafond-cible', `${att.rcr_rate}% — ${(att.plafond_cible_cents / 100).toFixed(2)} €`],
                ['Émise le', new Date(att.created_at).toLocaleDateString('fr-FR')],
                ['Expire le', att.date_expiration ? new Date(att.date_expiration).toLocaleDateString('fr-FR') : '—']].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-b border-white/[0.06] pb-1">
                  <dt className="text-white/45">{k}</dt><dd className="text-white/90 text-right">{v}</dd>
                </div>
              ))}
            </dl>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-white/40 mb-1">Signatures</p>
              {['fournisseur', 'oscop', 'kdmarche'].map((k) => {
                const s = att.signatures?.[k];
                return (
                  <p key={k} className="text-xs text-white/75 flex items-center gap-1.5">
                    {s ? <CheckCircle2 size={11} className="text-[#7BC94E]" /> : <Clock size={11} className="text-[#FBBF24]" />}
                    <b className="capitalize">{k === 'kdmarche' ? 'KDMARCHÉ PRO' : k === 'oscop' ? "O'SCOP" : 'Fournisseur'}</b>
                    {s ? ` — ${s.name} · ${new Date(s.at).toLocaleDateString('fr-FR')}` : ' — en attente'}
                  </p>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
