import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { KeyRound, BookOpen, ArrowLeft, Activity, Gauge, Loader2, Webhook } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SCOPE_LABELS = {
  'catalog:read': 'Catalogue (lecture)', 'orders:read': 'Commandes (lecture)',
  'territories:read': 'Territoires (lecture)', 'stock:write': 'Stock (écriture)',
};

const KeyCard = ({ k }) => {
  const quota = k.monthly_quota || 10000;
  const usage = k.month_usage || 0;
  const pct = Math.min(Math.round((usage / quota) * 100), 100);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5" data-testid={`dev-key-card-${k.id}`}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <p className="text-white font-semibold flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-[#D9B35A]" /> {k.name}
          {!k.is_active && <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300">DÉSACTIVÉE</span>}
        </p>
        <code className="text-xs text-white/50">{k.prefix}</code>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-4">
        {(k.scopes || []).map((s) => (
          <span key={s} className="px-2 py-0.5 rounded-full text-[10px] bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/30">{SCOPE_LABELS[s] || s}</span>
        ))}
      </div>
      <div className="mb-4">
        <div className="flex justify-between text-xs text-white/55 mb-1.5">
          <span className="flex items-center gap-1.5"><Gauge className="w-3.5 h-3.5 text-[#D9B35A]" /> Quota mensuel</span>
          <span data-testid={`dev-key-usage-${k.id}`}>{usage} / {quota} requêtes</span>
        </div>
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct > 85 ? '#EF4444' : 'linear-gradient(90deg, #D9B35A, #F2D07A)' }} />
        </div>
      </div>
      <p className="text-xs text-white/45 flex items-center gap-1.5 mb-2">
        <Activity className="w-3.5 h-3.5 text-[#D9B35A]" /> Derniers appels
        {k.last_used_at && <span className="text-white/35">· dernier : {new Date(k.last_used_at).toLocaleString('fr-FR')}</span>}
      </p>
      {(k.last_calls || []).length ? (
        <div className="max-h-48 overflow-y-auto space-y-1" data-testid={`dev-key-calls-${k.id}`}>
          {k.last_calls.map((c, i) => (
            <div key={`${c.ts}-${i}`} className="flex items-center gap-2 text-[11px] px-2 py-1 rounded bg-black/25">
              <span className="font-bold w-12" style={{ color: c.method === 'GET' ? '#10B981' : '#F59E0B' }}>{c.method}</span>
              <code className="text-white/70 flex-1 truncate">{c.path}</code>
              <span className="text-white/35">{new Date(c.ts).toLocaleString('fr-FR')}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-white/35">Aucun appel enregistré pour le moment.</p>
      )}

      <div className="mt-4 pt-3 border-t border-white/10">
        <p className="text-xs text-white/45 flex items-center gap-1.5 mb-2">
          <Webhook className="w-3.5 h-3.5 text-[#D9B35A]" /> Webhook ERP
          {k.webhook_url
            ? <code className="text-white/60 truncate">{k.webhook_url}</code>
            : <span className="text-white/30">non configuré — demandez à l'administrateur</span>}
        </p>
        {k.webhook_url && k.webhook_secret && (
          <p className="text-[10px] text-white/35 mb-2">Secret de signature (header <code>X-KDM-Signature</code> = sha256 HMAC du body) : <code className="text-[#E9CF8E]">{k.webhook_secret}</code></p>
        )}
        {(k.last_deliveries || []).length > 0 && (
          <div className="max-h-36 overflow-y-auto space-y-1" data-testid={`dev-key-deliveries-${k.id}`}>
            {k.last_deliveries.map((d, i) => (
              <div key={`${d.ts}-${i}`} className="flex items-center gap-2 text-[11px] px-2 py-1 rounded bg-black/25">
                <span className="font-bold" style={{ color: d.ok ? '#10B981' : '#EF4444' }}>{d.ok ? '✓' : '✗'} {d.status_code || 'ERR'}</span>
                <span className="text-white/60">{d.event}</span>
                <code className="text-white/45 flex-1 truncate">{d.order_id}</code>
                <span className="text-white/35">{new Date(d.ts).toLocaleString('fr-FR')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default function PartnerDevPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/partner/dev/keys`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : r.json().then((d) => Promise.reject(new Error(d.detail || 'Connexion requise')))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="min-h-screen text-white px-5 py-10" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #1A092D 100%)' }} data-testid="partner-dev-page">
      <div className="max-w-[860px] mx-auto">
        <Link to="/" className="text-xs text-white/50 hover:text-white inline-flex items-center gap-1.5 mb-6">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à l'accueil
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-3 mb-2">
          <h1 className="text-4xl font-bold tracking-tight flex items-center gap-3">
            <KeyRound className="w-8 h-8 text-[#D9B35A]" /> Espace Développeur
          </h1>
          <Link to="/docs-api" className="text-sm text-[#D9B35A] hover:underline inline-flex items-center gap-1.5" data-testid="dev-docs-link">
            <BookOpen className="w-4 h-4" /> Documentation API
          </Link>
        </div>
        <p className="text-white/60 text-sm mb-8">Vos clés API ERP, quotas mensuels et journal des derniers appels.</p>

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-400/10 p-5 text-sm text-red-200" data-testid="dev-error">
            {error} — <Link to="/connexion" className="underline">connectez-vous</Link> avec le compte associé à votre clé API.
          </div>
        )}
        {!error && !data && <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>}
        {data && !data.items.length && (
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-6 text-sm text-white/55" data-testid="dev-no-keys">
            Aucune clé API n'est rattachée à <strong className="text-white/80">{data.email}</strong>.
            Contactez l'administrateur de la plateforme pour obtenir votre accès ERP.
          </div>
        )}
        <div className="space-y-4">
          {(data?.items || []).map((k) => <KeyCard key={k.id} k={k} />)}
        </div>
      </div>
    </div>
  );
}
