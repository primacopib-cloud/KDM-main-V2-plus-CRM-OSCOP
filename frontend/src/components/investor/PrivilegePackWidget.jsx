import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown, FileDown, ArrowRight, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, apiCall, getAuthHeaders } from '../../services/http';

const fmtEur = (n) => `${Number(n).toLocaleString('fr-FR')} €`;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('fr-FR') : '—');
const STATUS_LABEL = {
  ACTIVE: ['Actif', 'text-emerald-300 border-emerald-400/40 bg-emerald-500/10'],
  PENDING_TRANSFER: ['Virement en attente', 'text-amber-300 border-amber-400/40 bg-amber-500/10'],
  PENDING: ['Paiement en attente', 'text-white/50 border-white/20 bg-white/5'],
};

// Widget espace investisseur : mon pack Privilège, crédits bonifiés, convention PDF
export const PrivilegePackWidget = () => {
  const [data, setData] = useState(null);
  const load = () => apiCall('/investor/privilege/me').then(setData).catch(() => {});

  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get('priv_session');
    if (sid) {
      apiCall('/investor/privilege/activate', { method: 'POST', body: JSON.stringify({ session_id: sid }) })
        .then(() => { toast.success('👑 Abonnement Privilège Investisseur activé !'); load(); })
        .catch((e) => { toast.error(e.message); load(); });
    } else load();
  }, []);

  const downloadPdf = async () => {
    const r = await fetch(`${API}/investor/privilege/convention/pdf`, { headers: getAuthHeaders(), credentials: 'include' });
    if (!r.ok) { toast.error('Convention indisponible'); return; }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'convention-fcrl.pdf';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const subs = data?.subscriptions || [];
  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mb-8" data-testid="privilege-pack-widget">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Crown className="w-5 h-5 text-[#D9B35A]" /> Abonnement Privilège — Packs FCRL
        </h2>
        {data?.credits_eur > 0 && (
          <span className="px-3 py-1 rounded-full text-xs font-black text-[#F2D07A] border border-[#D9B35A]/50 bg-[#D9B35A]/10"
            data-testid="privilege-credits-balance">
            {fmtEur(data.credits_eur)} de crédits bonifiés
          </span>
        )}
      </div>
      {subs.length === 0 ? (
        <div className="mt-3">
          <p className="text-white/60 text-sm">
            Placez votre trésorerie dans un pack de crédits bonifiés (+15 à +30 %) qui préfinance les stocks
            et conteneurs LOGI'SCOP des acheteurs pro du réseau.
          </p>
          <Link to="/investisseurs-privilege" data-testid="privilege-discover-link"
            className="inline-flex items-center gap-2 mt-3 px-5 h-10 rounded-full bg-[#D9B35A] text-black text-xs font-bold hover:bg-[#E9CF8E] transition-colors on-gold">
            Découvrir les packs Bronze · Argent · Or <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {subs.map((s) => {
            const [label, cls] = STATUS_LABEL[s.status] || STATUS_LABEL.PENDING;
            return (
              <div key={s.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4" data-testid={`privilege-sub-${s.reference}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold">{s.pack_name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${cls}`}
                    data-testid={`privilege-sub-status-${s.reference}`}>{label}</span>
                  <span className="text-[10px] text-white/40 font-mono">{s.reference}</span>
                </div>
                <p className="text-xs text-white/60 mt-1.5">
                  Apport {fmtEur(s.amount_eur)} → <b className="text-[#F2D07A]">{fmtEur(s.credits_eur)}</b> de
                  crédits (+{s.bonus_pct} %) · signée le {fmtDate(s.convention?.signed_at)} par {s.convention?.signer_name}
                </p>
                {s.privileges?.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {s.privileges.map((p) => (
                      <li key={p} className="flex items-start gap-1.5 text-[10.5px] text-white/55">
                        <CheckCircle2 className="w-3 h-3 text-[#D9B35A] shrink-0 mt-px" /> {p}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
          <button onClick={downloadPdf} data-testid="privilege-convention-pdf-btn"
            className="inline-flex items-center gap-2 px-4 h-9 rounded-full border border-white/25 text-xs font-bold hover:bg-white/10 transition-colors">
            <FileDown className="w-3.5 h-3.5" /> Télécharger ma convention signée (PDF)
          </button>
        </div>
      )}
    </div>
  );
};
