import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowRight, CheckCircle2, Copy, Download, Eye, EyeOff, FlaskConical, KeyRound, Loader2, Save, Webhook } from 'lucide-react';
import { getAuthHeaders, getSessionToken } from '../../services/http';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const frDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch { return iso; } };

const WebhookSandbox = ({ sub, onSaved }) => {
  const [url, setUrl] = useState(sub.webhook_url || '');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const dirty = url !== (sub.webhook_url || '');

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api-subscription/me/webhook`, {
        method: 'PUT', headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify({ webhook_url: url }),
      });
      const d = await r.json();
      if (!r.ok) toast.error(d.detail || 'Enregistrement impossible');
      else { toast.success(url ? 'Webhook enregistré' : 'Webhook retiré'); onSaved(); }
    } catch { toast.error('Erreur réseau'); }
    setSaving(false);
  };

  const test = async () => {
    setTesting(true);
    try {
      const r = await fetch(`${API}/api-subscription/me/webhook/test`, {
        method: 'POST', headers: getAuthHeaders(), credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) toast.error(d.detail || 'Test impossible');
      else if (d.ok) toast.success(`Webhook OK — votre endpoint a répondu ${d.status_code} ✓`);
      else toast.error(`Échec du webhook : ${d.error || `HTTP ${d.status_code}`}`);
    } catch { toast.error('Erreur réseau'); }
    setTesting(false);
  };

  return (
    <div className="mt-4 rounded-xl border border-white/15 bg-black/20 p-4" data-testid="api-webhook-sandbox">
      <p className="text-xs font-bold uppercase tracking-wide text-white/50 mb-1 flex items-center gap-1.5">
        <Webhook className="w-3.5 h-3.5 text-[#D9B35A]" /> Webhook commandes (temps réel)
      </p>
      <p className="text-[11px] text-white/45 m-0 mb-2">
        Recevez chaque commande LOLODRIVE de votre relais (payée, prête, retirée) sur votre outil — testez votre
        endpoint avant la mise en production.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input value={url} onChange={(e) => setUrl(e.target.value)}
          placeholder="https://mon-outil.fr/hooks/lolodrive" data-testid="api-webhook-url-input"
          className="h-9 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white placeholder:text-white/30 flex-1 min-w-[220px]" />
        {dirty && (
          <button type="button" onClick={save} disabled={saving} data-testid="api-webhook-save-btn"
            className="h-9 px-3 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 text-[#1F0A33] disabled:opacity-60"
            style={{ background: '#D4AF37' }}>
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Enregistrer
          </button>
        )}
        {!dirty && sub.webhook_url && (
          <button type="button" onClick={test} disabled={testing} data-testid="api-webhook-test-btn"
            className="h-9 px-3 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 border border-emerald-400/40 text-emerald-300 hover:bg-emerald-400/10 disabled:opacity-60">
            {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FlaskConical className="w-3.5 h-3.5" />}
            {testing ? 'Test en cours…' : 'Tester mon webhook'}
          </button>
        )}
      </div>
    </div>
  );
};

export const ApiSubscribeCard = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const pollCount = useRef(0);

  const loadMe = useCallback(async () => {
    if (!getSessionToken()) return;
    try {
      const r = await fetch(`${API}/api-subscription/me`, { headers: getAuthHeaders(), credentials: 'include' });
      if (r.ok) setSub((await r.json()).subscription);
    } catch { /* silencieux */ }
  }, []);
  useEffect(() => { loadMe(); }, [loadMe]);

  useEffect(() => {
    const sessionId = params.get('api_session_id');
    if (!sessionId) return;
    setPolling(true);
    const poll = async () => {
      pollCount.current += 1;
      try {
        const r = await fetch(`${API}/api-subscription/checkout-status/${sessionId}`, { headers: getAuthHeaders(), credentials: 'include' });
        const d = await r.json();
        if (r.ok && d.status === 'ACTIVE') {
          setPolling(false);
          toast.success(`Abonnement API ${d.reference} activé — votre clé vous a été envoyée par email 🔑`);
          params.delete('api_session_id');
          setParams(params, { replace: true });
          loadMe();
          return;
        }
      } catch { /* retry */ }
      if (pollCount.current < 12) setTimeout(poll, 2500);
      else { setPolling(false); toast.error('Paiement en cours de confirmation — rechargez la page dans un instant.'); }
    };
    poll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe = async () => {
    if (!getSessionToken()) {
      toast.info('Connectez-vous pour souscrire l\'abonnement API');
      navigate('/connexion?next=/coop-api');
      return;
    }
    setLoading(true);
    try {
      const r = await fetch(`${API}/api-subscription/checkout`, {
        method: 'POST', headers: getAuthHeaders(), credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Souscription impossible'); setLoading(false); return; }
      window.location.href = d.checkout_url;
    } catch { toast.error('Erreur réseau'); setLoading(false); }
  };

  const copyKey = () => { navigator.clipboard.writeText(sub.api_key); toast.success('Clé API copiée'); };

  const downloadInvoice = async () => {
    try {
      const r = await fetch(`${API}/api-subscription/me/invoice.pdf`, { headers: getAuthHeaders(), credentials: 'include' });
      if (!r.ok) return toast.error('Facture indisponible');
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `facture-${sub.reference}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch { toast.error('Téléchargement impossible'); }
  };

  if (sub && !sub.expired) {
    return (
      <div className="mt-10 rounded-[24px] p-7 border border-[#8CC63E]/40"
        style={{ background: 'radial-gradient(120% 160% at 50% -20%, rgba(140,198,62,0.12), rgba(20,8,38,0.5))' }}
        data-testid="api-my-subscription">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <CheckCircle2 className="w-5 h-5 text-[#8CC63E]" />
          <h2 className="font-display text-2xl m-0 text-[#B6E27A]">Votre abonnement API est actif</h2>
          {sub.early_renewal && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold text-[#2a0c4a]"
              style={{ background: 'linear-gradient(135deg, #F5A623 0%, #D9B35A 100%)' }}
              data-testid="api-loyalty-badge">
              ⭐ Fidélité — renouvellement anticipé
            </span>
          )}
        </div>
        <p className="text-white/70 text-sm mb-4" data-testid="api-sub-details">
          Référence <b className="text-white/90">{sub.reference}</b> · payé le {frDate(sub.paid_at)} · valide
          jusqu'au <b className="text-white/90">{frDate(sub.valid_until)}</b> · {Number(sub.amount_eur).toLocaleString('fr-FR')} € / an
        </p>
        {sub.usage && (
          <div className="mb-4 rounded-xl border border-white/15 bg-black/20 p-4" data-testid="api-sub-usage">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs font-bold uppercase tracking-wide text-white/50 m-0">Consommation du mois</p>
              <p className="text-xs text-white/80 font-semibold m-0" data-testid="api-sub-usage-count">
                {Number(sub.usage.month_usage).toLocaleString('fr-FR')} / {Number(sub.usage.monthly_quota).toLocaleString('fr-FR')} requêtes
              </p>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-[#8CC63E] to-[#D9B35A]"
                style={{ width: `${Math.min(100, Math.max(sub.usage.month_usage > 0 ? 2 : 0, (sub.usage.month_usage / sub.usage.monthly_quota) * 100))}%` }} />
            </div>
            <p className="text-[10px] text-white/35 m-0 mt-1">{Number(sub.usage.requests_count).toLocaleString('fr-FR')} requêtes depuis l'activation</p>
          </div>
        )}
        <div className="rounded-xl border border-white/15 bg-black/30 p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-white/50 mb-2 flex items-center gap-1.5">
            <KeyRound className="w-3.5 h-3.5 text-[#D9B35A]" /> Votre clé API (header X-API-Key)
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <code className="text-[13px] text-[#B6E27A] break-all flex-1 min-w-[200px]" data-testid="api-key-value">
              {showKey ? sub.api_key : `${sub.api_key_prefix || 'kdm_live_…'}${'•'.repeat(24)}`}
            </code>
            <button type="button" onClick={() => setShowKey((v) => !v)} data-testid="api-key-reveal-btn"
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white" title={showKey ? 'Masquer' : 'Révéler'}>
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
            <button type="button" onClick={copyKey} data-testid="api-key-copy-btn"
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white" title="Copier">
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        <WebhookSandbox sub={sub} onSaved={loadMe} />
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" onClick={downloadInvoice} data-testid="api-sub-invoice-btn"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white border border-white/25 hover:bg-white/5">
            <Download className="w-4 h-4" /> Télécharger ma facture acquittée
          </button>
          {sub.renewable && (
            <button type="button" onClick={subscribe} disabled={loading} data-testid="api-sub-renew-btn"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-[#2a0c4a] disabled:opacity-60"
              style={{ background: 'linear-gradient(135deg, #F5A623 0%, #D9B35A 100%)' }}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Renouveler — 2 500 € (échéance le {frDate(sub.valid_until)})
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-10 rounded-[24px] p-7 border border-[#D9B35A]/30 text-center"
      style={{ background: 'radial-gradient(120% 160% at 50% -20%, rgba(217,179,90,0.14), rgba(20,8,38,0.5))' }}
      data-testid="api-subscription-cta">
      <h2 className="font-display text-2xl mb-2 text-[#E9CF8E]">Abonnement annuel — 2 500 € / an</h2>
      <p className="text-white/70 text-sm max-w-xl mx-auto mb-4">
        Réservé <b>exclusivement aux relais LOLODRIVE</b> (gérants de LOLO POINT) pour la gestion de leur
        catalogue. Dès le paiement confirmé, votre <b>clé API est générée automatiquement</b>,
        envoyée par email avec votre <b>facture acquittée O'SCOP</b>, et reste consultable ici à tout moment.
      </p>
      <ul className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-white/75 mb-6 list-none p-0">
        {['Clé API personnelle', 'Facture acquittée O\'SCOP', 'Validité 12 mois', 'Support technique coopératif'].map((li) => (
          <li key={li} className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-[#8CC63E]" /> {li}</li>
        ))}
      </ul>
      {polling ? (
        <div className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-[#E9CF8E] border border-[#D9B35A]/40" data-testid="api-sub-polling">
          <Loader2 className="w-4 h-4 animate-spin" /> Confirmation du paiement en cours…
        </div>
      ) : (
        <div className="flex flex-wrap justify-center gap-3">
          <button type="button" onClick={subscribe} disabled={loading} data-testid="api-cta-souscription"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-[#2a0c4a] disabled:opacity-60"
            style={{ background: 'linear-gradient(135deg, #F5A623 0%, #D9B35A 100%)' }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Souscrire l'abonnement annuel — 2 500 € <ArrowRight className="w-4 h-4" />
          </button>
          <Link to="/adhesion-vendeur" data-testid="api-cta-adhesion"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white border border-white/25 hover:bg-white/5">
            Adhérer à la centrale
          </Link>
        </div>
      )}
      {sub?.expired && (
        <p className="text-xs text-amber-300/90 mt-3 m-0" data-testid="api-sub-expired">
          Votre abonnement {sub.reference} a expiré le {frDate(sub.valid_until)} — renouvelez-le pour réactiver votre accès.
        </p>
      )}
    </div>
  );
};
