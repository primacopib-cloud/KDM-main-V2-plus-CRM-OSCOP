import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import LolodriveLayout, { SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { lolodriveAPI } from '../services/api';

const MAX_ATTEMPTS = 8;
const POLL_INTERVAL_MS = 1500;

export default function PaymentReturnPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const sessionId = params.get('session_id');
  const kind = params.get('kind');
  const ref = params.get('ref');

  const [status, setStatus] = useState({ phase: 'polling', message: 'Vérification du paiement…' });
  const [details, setDetails] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setStatus({ phase: 'error', message: 'Session de paiement absente.' });
      return;
    }
    let attempts = 0;
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      try {
        const r = await lolodriveAPI.checkoutStatus(sessionId);
        setDetails(r);
        if (r.payment_status === 'paid') {
          setStatus({ phase: 'success', message: 'Paiement confirmé ✅' });
          return;
        }
        if (r.status === 'expired' || r.payment_status === 'failed') {
          setStatus({ phase: 'failed', message: 'Paiement échoué ou expiré.' });
          return;
        }
        attempts += 1;
        if (attempts >= MAX_ATTEMPTS) {
          setStatus({ phase: 'timeout', message: 'Statut inconnu après plusieurs tentatives.' });
          return;
        }
        setStatus({ phase: 'polling', message: `Vérification… (${attempts}/${MAX_ATTEMPTS})` });
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (e) {
        setStatus({ phase: 'error', message: e.message });
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [sessionId]);

  const nextRoute = () => {
    if (kind === 'PASS' || kind === 'RECHARGE') return '/pass';
    if (kind === 'ORDER') return '/pass';
    return '/lolodrive';
  };

  return (
    <LolodriveLayout title="Confirmation paiement" subtitle="Stripe Checkout — mode test">
      <SectionCard className="text-center">
        <div className="py-12">
          {status.phase === 'polling' && (
            <>
              <Loader2 className="w-12 h-12 mx-auto mb-4 text-[#D9B35A] animate-spin" />
              <h2 className="text-2xl font-bold mb-2">Vérification en cours</h2>
              <p className="text-white/60 text-sm">{status.message}</p>
            </>
          )}
          {status.phase === 'success' && (
            <>
              <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-emerald-400" data-testid="payment-success-icon" />
              <h2 className="text-2xl font-bold mb-2 text-emerald-400">Paiement réussi</h2>
              <p className="text-white/70 text-sm">{successMessage(kind)}</p>
              {details && (
                <div className="mt-4 inline-flex flex-col gap-1 p-4 rounded-xl bg-white/[0.03] border border-white/[0.07] text-xs">
                  <KV label="Montant" value={fmtEUR(details.amount_total || 0)} />
                  <KV label="Type" value={details.kind} />
                  <KV label="Session" value={(sessionId || '').slice(0, 28) + '…'} />
                </div>
              )}
              <div className="mt-6">
                <Button onClick={() => navigate(nextRoute())} size="lg"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}
                  data-testid="goto-pass-btn">
                  Voir mon espace PASS <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </>
          )}
          {(status.phase === 'failed' || status.phase === 'timeout' || status.phase === 'error') && (
            <>
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-400" />
              <h2 className="text-2xl font-bold mb-2 text-red-400">Paiement non confirmé</h2>
              <p className="text-white/70 text-sm">{status.message}</p>
              <div className="mt-6 flex gap-2 justify-center">
                <Button variant="outline" onClick={() => navigate('/pass')}>Retour</Button>
                <Button onClick={() => window.location.reload()}>Vérifier à nouveau</Button>
              </div>
            </>
          )}
        </div>
      </SectionCard>
    </LolodriveLayout>
  );
}

const successMessage = (kind) => ({
  PASS: 'Votre PASS Vie Chère est désormais actif. 600 UC ont été crédités sur votre wallet.',
  RECHARGE: 'Votre wallet UC a été rechargé.',
  ORDER: 'Votre commande est confirmée et entre en préparation.',
}[kind] || 'Opération confirmée.');

const KV = ({ label, value }) => (
  <div className="flex justify-between gap-4">
    <span className="text-white/40">{label}</span>
    <span className="font-medium">{value}</span>
  </div>
);
