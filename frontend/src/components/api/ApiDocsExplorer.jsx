import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { BookOpen, ChevronDown, Copy } from 'lucide-react';
import { getAuthHeaders, getSessionToken } from '../../services/http';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BASE_V1 = `${process.env.REACT_APP_BACKEND_URL}/api/public/v1`;

const ENDPOINTS = [
  { method: 'GET', path: '/ping', title: 'Tester ma clé', desc: 'Vérifie la validité de la clé et renvoie ses scopes + consommation.', curl: (k) => `curl "${BASE_V1}/ping" \\\n  -H "X-API-Key: ${k}"` },
  { method: 'GET', path: '/products', title: 'Lister le catalogue', desc: 'Produits actifs de la centrale (pagination limit/offset, filtre category_id).', curl: (k) => `curl "${BASE_V1}/products?limit=20&offset=0" \\\n  -H "X-API-Key: ${k}"` },
  { method: 'GET', path: '/products/{id}', title: 'Fiche produit', desc: 'Détail complet d\'un produit par son identifiant.', curl: (k) => `curl "${BASE_V1}/products/PRODUCT_ID" \\\n  -H "X-API-Key: ${k}"` },
  { method: 'PATCH', path: '/products/{id}/stock', title: 'Synchroniser un stock', desc: 'Met à jour le stock d\'un produit depuis votre caisse ou ERP (scope stock:write).', curl: (k) => `curl -X PATCH "${BASE_V1}/products/PRODUCT_ID/stock" \\\n  -H "X-API-Key: ${k}" \\\n  -H "Content-Type: application/json" \\\n  -d '{"stock_qty": 42}'` },
  { method: 'GET', path: '/orders', title: 'Lister les commandes', desc: 'Commandes mutualisées (filtres status, zone_code, pagination).', curl: (k) => `curl "${BASE_V1}/orders?zone_code=GUADELOUPE&limit=20" \\\n  -H "X-API-Key: ${k}"` },
  { method: 'GET', path: '/orders/{id}', title: 'Détail commande', desc: 'Une commande par id ou numéro de commande.', curl: (k) => `curl "${BASE_V1}/orders/KDM-20260716" \\\n  -H "X-API-Key: ${k}"` },
  { method: 'GET', path: '/territories', title: 'Zones & territoires', desc: 'Liste des zones tarifaires actives de la centrale.', curl: (k) => `curl "${BASE_V1}/territories" \\\n  -H "X-API-Key: ${k}"` },
];

const METHOD_COLORS = { GET: 'bg-[#8CC63E]/15 text-[#B6E27A] border-[#8CC63E]/40', PATCH: 'bg-amber-400/15 text-amber-300 border-amber-400/40' };

export const ApiDocsExplorer = () => {
  const [apiKey, setApiKey] = useState(null);
  const [open, setOpen] = useState(0);

  useEffect(() => {
    if (!getSessionToken()) return;
    fetch(`${API}/api-subscription/me`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.subscription?.api_key && !d.subscription.expired) setApiKey(d.subscription.api_key); })
      .catch(() => {});
  }, []);

  const keyShown = apiKey || 'VOTRE_CLE_API';
  const copy = (text) => { navigator.clipboard.writeText(text); toast.success('Exemple copié' + (apiKey ? ' avec votre clé API' : '')); };

  return (
    <div className="mt-10" data-testid="api-docs-explorer">
      <div className="flex items-center gap-2 mb-1.5">
        <BookOpen className="w-4 h-4 text-[#D9B35A]" />
        <h2 className="font-display text-2xl m-0">Documentation interactive</h2>
      </div>
      <p className="text-white/60 text-sm mb-4">
        {apiKey
          ? 'Vos exemples sont pré-remplis avec votre clé API personnelle — copiez, collez, exécutez.'
          : 'Exemples prêts à copier — une fois abonné, votre clé API personnelle sera automatiquement insérée.'}
      </p>
      <div className="space-y-2">
        {ENDPOINTS.map((ep, i) => (
          <div key={ep.path + ep.method} className="rounded-[16px] border border-white/10 overflow-hidden bg-white/[0.03]"
            data-testid={`api-doc-${ep.method.toLowerCase()}-${ep.path.replace(/[/{}]/g, '')}`}>
            <button type="button" onClick={() => setOpen(open === i ? -1 : i)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.03]"
              data-testid={`api-doc-toggle-${i}`}>
              <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold border ${METHOD_COLORS[ep.method]}`}>{ep.method}</span>
              <code className="text-[13px] text-white/85">{ep.path}</code>
              <span className="text-xs text-white/45 hidden sm:inline flex-1 truncate">{ep.title}</span>
              <ChevronDown className={`w-4 h-4 text-white/40 transition-transform ${open === i ? 'rotate-180' : ''}`} />
            </button>
            {open === i && (
              <div className="px-4 pb-4">
                <p className="text-xs text-white/55 mb-2 m-0">{ep.desc}</p>
                <div className="relative rounded-xl bg-[#150724] border border-white/10">
                  <pre className="m-0 p-4 pr-12 text-[12px] leading-relaxed overflow-x-auto text-[#B6E27A]">{ep.curl(keyShown)}</pre>
                  <button type="button" onClick={() => copy(ep.curl(keyShown))} data-testid={`api-doc-copy-${i}`}
                    className="absolute top-2 right-2 p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white" title="Copier l'exemple">
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
