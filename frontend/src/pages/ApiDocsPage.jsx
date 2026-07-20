import { Link } from 'react-router-dom';
import { BookOpen, KeyRound, ArrowLeft } from 'lucide-react';

const BASE = process.env.REACT_APP_BACKEND_URL;

const ENDPOINTS = [
  { method: 'GET', path: '/api/public/v1/ping', scope: '—', desc: 'Vérifie la validité de la clé et renvoie ses scopes.' },
  { method: 'GET', path: '/api/public/v1/products', scope: 'catalog:read', desc: 'Liste paginée des produits actifs. Params : limit, offset, category_id.' },
  { method: 'GET', path: '/api/public/v1/products/{id}', scope: 'catalog:read', desc: "Détail d'un produit." },
  { method: 'PATCH', path: '/api/public/v1/products/{id}/stock', scope: 'stock:write', desc: 'Synchronise le stock depuis votre ERP. Body : {"stock_qty": 120}.' },
  { method: 'GET', path: '/api/public/v1/orders', scope: 'orders:read', desc: 'Liste paginée des commandes. Params : limit, offset, status, zone_code.' },
  { method: 'GET', path: '/api/public/v1/orders/{id}', scope: 'orders:read', desc: "Détail d'une commande (id ou numéro), incluant le statut logistique." },
  { method: 'GET', path: '/api/public/v1/territories', scope: 'territories:read', desc: 'Territoires actifs de la plateforme.' },
];

const methodColor = (m) => (m === 'GET' ? '#10B981' : m === 'PATCH' ? '#F59E0B' : '#D9B35A');

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen text-white px-5 py-10" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #1A092D 100%)' }} data-testid="api-docs-page">
      <div className="max-w-[860px] mx-auto">
        <Link to="/" className="text-xs text-white/50 hover:text-white inline-flex items-center gap-1.5 mb-6">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à l'accueil
        </Link>
        <Link to="/espace-developpeur" className="text-xs text-[#D9B35A] hover:underline inline-flex items-center gap-1.5 mb-6 ml-4" data-testid="docs-dev-space-link">
          <KeyRound className="w-3.5 h-3.5" /> Mon espace développeur
        </Link>
        <h1 className="text-4xl font-bold tracking-tight flex items-center gap-3 mb-2">
          <BookOpen className="w-8 h-8 text-[#D9B35A]" /> API publique v1 — Connecteurs ERP
        </h1>
        <p className="text-white/65 text-sm mb-8 max-w-[65ch]">
          Connectez votre ERP à la Communityplace KDMARCHÉ × O'SCOP : catalogue, commandes, stocks et territoires.
          Les clés API sont délivrées par l'administrateur de la plateforme.
        </p>

        <div className="rounded-2xl border border-[#D9B35A]/30 p-5 mb-8" style={{ background: 'rgba(217,179,90,0.07)' }}>
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-2"><KeyRound className="w-4 h-4 text-[#D9B35A]" /> Authentification</h2>
          <p className="text-sm text-white/70 mb-3">Chaque requête doit inclure votre clé dans le header <code className="text-[#D9B35A]">X-API-Key</code>. Chaque clé possède des scopes (permissions) précis.</p>
          <pre className="bg-black/40 rounded-xl p-4 text-xs text-emerald-300 overflow-x-auto">{`curl "${BASE}/api/public/v1/ping" \\
  -H "X-API-Key: kdm_live_xxxxxxxxxxxxxxxx"`}</pre>
        </div>

        <h2 className="text-lg font-semibold mb-3">Endpoints</h2>
        <div className="space-y-3 mb-10">
          {ENDPOINTS.map((e) => (
            <div key={`${e.method}-${e.path}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="px-2 py-0.5 rounded-md text-[11px] font-bold" style={{ background: `${methodColor(e.method)}22`, color: methodColor(e.method) }}>{e.method}</span>
                <code className="text-sm text-white/90">{e.path}</code>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-white/50 ml-auto">scope : {e.scope}</span>
              </div>
              <p className="text-xs text-white/55 mt-2">{e.desc}</p>
            </div>
          ))}
        </div>

        <h2 className="text-lg font-semibold mb-3">Exemples</h2>
        <p className="text-xs text-white/50 mb-2">Lister les produits :</p>
        <pre className="bg-black/40 rounded-xl p-4 text-xs text-emerald-300 overflow-x-auto mb-4">{`curl "${BASE}/api/public/v1/products?limit=20" \\
  -H "X-API-Key: kdm_live_xxxxxxxxxxxxxxxx"`}</pre>
        <p className="text-xs text-white/50 mb-2">Synchroniser un stock depuis votre ERP :</p>
        <pre className="bg-black/40 rounded-xl p-4 text-xs text-emerald-300 overflow-x-auto mb-4">{`curl -X PATCH "${BASE}/api/public/v1/products/PRODUCT_ID/stock" \\
  -H "X-API-Key: kdm_live_xxxxxxxxxxxxxxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"stock_qty": 120}'`}</pre>

        <div className="rounded-2xl border border-[#D9B35A]/30 p-5 mb-8" style={{ background: 'rgba(217,179,90,0.07)' }} data-testid="webhook-doc-section">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-2"><KeyRound className="w-4 h-4 text-[#D9B35A]" /> Webhooks ERP</h2>
          <p className="text-sm text-white/70 mb-3">
            Configurez une URL de webhook sur votre clé (via l'administrateur) pour être notifié en temps réel
            des changements de statut de commande, sans interroger l'API. Événements : <code className="text-[#D9B35A]">order.status_changed</code>,{' '}
            <code className="text-[#D9B35A]">order.logistics_updated</code>.
            Chaque livraison est signée : header <code className="text-[#D9B35A]">X-KDM-Signature</code> = <code>sha256=HMAC-SHA256(secret, body)</code>.
          </p>
          <pre className="bg-black/40 rounded-xl p-4 text-xs text-emerald-300 overflow-x-auto">{`POST https://votre-erp.com/hooks/kdm
X-KDM-Event: order.status_changed
X-KDM-Signature: sha256=3f7a...

{"event": "order.status_changed", "ts": "...",
 "order": {"id": "...", "order_number": "KDM-...", "status": "CONFIRMED", ...},
 "data": {"previous_status": "PENDING", "new_status": "CONFIRMED"}}`}</pre>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-xs text-white/55">
          <p className="mb-1"><strong className="text-white/80">Codes d'erreur :</strong> 401 clé manquante/invalide · 403 clé désactivée ou scope insuffisant · 404 ressource introuvable.</p>
          <p>Toutes les écritures ERP sont tracées dans le journal d'audit inviolable de la plateforme.</p>
        </div>
      </div>
    </div>
  );
}
