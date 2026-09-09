import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Truck, Package, BadgeCheck, CalendarClock } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const TRACK_STEPS = [['CONFIRMEE', 'Confirmée'], ['PREPARATION', 'Préparation'], ['EXPEDITION', 'Expédiée'], ['TRANSIT', 'En transit'], ['LIVREE', 'Livrée']];
const frDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch { return iso; } };

// Page publique de suivi logistique d'un financement (lien partageable, lecture seule, sans connexion)
export default function FinancingTrackingPage() {
  const { token } = useParams();
  const [fp, setFp] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/public/financing-products/track/${token}`)
      .then(async (r) => {
        if (!r.ok) throw new Error('Lien de suivi invalide ou expiré');
        setFp(await r.json());
      })
      .catch((e) => setError(e.message));
  }, [token]);

  const idx = fp ? TRACK_STEPS.findIndex(([k]) => k === fp.tracking_status) : -1;

  return (
    <div className="min-h-screen px-4 py-10 flex items-start justify-center"
      style={{ background: 'linear-gradient(135deg, #1F0A33 0%, #2B1247 55%, #1F0A33 100%)' }}>
      <div className="w-full max-w-lg rounded-[24px] p-6 bg-white/[0.04] border border-white/10" data-testid="public-tracking-page">
        <div className="text-center mb-6">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[#D9B35A] font-bold m-0">O'SCOP — Centrale coopérative</p>
          <h1 className="text-xl font-bold text-white mt-2 mb-0">Suivi de financement</h1>
        </div>
        {error && (
          <p className="text-center text-red-300 text-sm" data-testid="tracking-error">⚠️ {error}</p>
        )}
        {fp && (
          <>
            <div className="rounded-[14px] p-4 bg-white/[0.03] border border-white/[0.08] mb-5">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="text-white font-bold">{fp.reference}</span>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                  fp.kind === 'LOGISTIQUE' ? 'text-sky-300 bg-sky-500/10 border-sky-400/40' : 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'}`}
                  data-testid="tracking-kind">
                  {fp.kind === 'LOGISTIQUE' ? <Truck className="w-3 h-3" /> : <Package className="w-3 h-3" />}
                  {fp.kind === 'LOGISTIQUE' ? 'Logistique' : 'Produit'}
                </span>
              </div>
              <p className="text-white/80 text-sm mt-1 mb-0">{fp.name}</p>
              <p className="text-[10px] text-white/45 mt-1 mb-0">Vendu et facturé par O'SCOP</p>
            </div>
            <div className="flex items-center mb-4" data-testid="tracking-stepper">
              {TRACK_STEPS.map(([key, label], i) => (
                <div key={key} className="flex-1 flex flex-col items-center relative">
                  {i > 0 && (
                    <span className={`absolute top-[9px] right-1/2 w-full h-0.5 ${i <= idx ? 'bg-[#8CC63E]' : 'bg-white/15'}`} />
                  )}
                  <span className={`relative z-10 w-4 h-4 rounded-full border-2 ${
                    i < idx ? 'bg-[#8CC63E] border-[#8CC63E]'
                      : i === idx ? 'bg-[#8CC63E] border-[#8CC63E] ring-2 ring-[#8CC63E]/30'
                      : 'bg-[#241243] border-white/25'}`} />
                  <span className={`mt-1.5 text-[10px] text-center leading-tight ${i <= idx ? 'text-[#8CC63E] font-bold' : 'text-white/40'}`}>{label}</span>
                </div>
              ))}
            </div>
            {fp.eta_delivery && (
              <p className="text-[#E9CF8E] text-sm font-semibold text-center" data-testid="tracking-eta">
                <CalendarClock className="w-4 h-4 inline mr-1" /> Livraison estimée : {frDate(fp.eta_delivery)}
              </p>
            )}
            {fp.receipt_confirmed_at && (
              <p className="text-[#8CC63E] text-sm font-bold text-center mt-2" data-testid="tracking-receipt">
                <BadgeCheck className="w-4 h-4 inline mr-1" /> Réception confirmée par l'investisseur le {frDate(fp.receipt_confirmed_at)}
              </p>
            )}
            {(fp.tracking_history || []).length > 0 && (
              <div className="mt-5 pt-4 border-t border-white/10 space-y-1.5" data-testid="tracking-history">
                {[...fp.tracking_history].reverse().map((h, i) => (
                  <p key={`${h.step}-${h.at}`} className="text-[12px] text-white/60 m-0">
                    {i === 0 ? '▶' : '·'} <b className="text-white/85">{h.label}</b> — {frDate(h.at)}
                  </p>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
