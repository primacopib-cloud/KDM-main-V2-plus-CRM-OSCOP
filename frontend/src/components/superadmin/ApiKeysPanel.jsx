import { useCallback, useEffect, useState } from 'react';
import { KeyRound, Plus, Trash2, Power, Copy, BookOpen, Webhook, Save, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35';

const SCOPE_LABELS = {
  'catalog:read': 'Catalogue (lecture)',
  'orders:read': 'Commandes (lecture)',
  'territories:read': 'Territoires (lecture)',
  'stock:write': 'Stock (écriture)',
};

const WebhookEditor = ({ k, onSaved }) => {
  const [url, setUrl] = useState(k.webhook_url || '');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const dirty = url !== (k.webhook_url || '');
  const save = async () => {
    setSaving(true);
    const r = await fetch(`${API}/admin/api-keys/${k.id}/webhook`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url: url }),
    });
    const d = await r.json();
    setSaving(false);
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(url ? 'Webhook ERP configuré' : 'Webhook retiré');
    onSaved();
  };
  const test = async () => {
    setTesting(true);
    const r = await fetch(`${API}/admin/api-keys/${k.id}/webhook/test`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    setTesting(false);
    if (!r.ok) return toast.error(d.detail || 'Test impossible');
    if (d.ok) toast.success(`Webhook OK — l'ERP a répondu ${d.status_code}`);
    else toast.error(`Échec du webhook : ${d.error || `HTTP ${d.status_code}`}`);
  };
  return (
    <div className="flex items-center gap-2 mt-2">
      <Webhook size={13} className="text-[#D9B35A] flex-shrink-0" />
      <input value={url} onChange={(e) => setUrl(e.target.value)}
        placeholder="URL webhook ERP (https://erp.partenaire.com/hooks/kdm)"
        data-testid={`webhook-url-input-${k.id}`}
        className="h-8 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-xs text-white placeholder:text-white/30 flex-1" />
      {dirty && (
        <button onClick={save} disabled={saving} data-testid={`webhook-save-${k.id}`}
          className="h-8 px-2.5 rounded-lg text-xs font-bold inline-flex items-center gap-1"
          style={{ background: '#D4AF37', color: '#1F0A33' }}>
          <Save size={12} /> OK
        </button>
      )}
      {!dirty && k.webhook_url && (
        <button onClick={test} disabled={testing} data-testid={`webhook-test-${k.id}`}
          className="h-8 px-2.5 rounded-lg text-xs font-bold inline-flex items-center gap-1 border border-emerald-400/40 text-emerald-300 hover:bg-emerald-400/10 disabled:opacity-50">
          <FlaskConical size={12} /> {testing ? 'Test…' : 'Tester'}
        </button>
      )}
      {k.webhook_secret && <code className="text-[10px] text-white/35 flex-shrink-0" title="Secret de signature HMAC">{k.webhook_secret.slice(0, 14)}…</code>}
    </div>
  );
};

export const ApiKeysPanel = () => {
  const [items, setItems] = useState([]);
  const [scopes, setScopes] = useState([]);
  const [form, setForm] = useState({ name: '', partner_email: '', scopes: ['catalog:read'], monthly_quota: 10000 });
  const [newKey, setNewKey] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/api-keys`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => { setItems(d.items || []); setScopes(d.valid_scopes || []); })
      .catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleScope = (s) => setForm((f) => ({
    ...f, scopes: f.scopes.includes(s) ? f.scopes.filter((x) => x !== s) : [...f.scopes, s],
  }));

  const create = async () => {
    if (!form.name.trim()) return toast.error('Nom requis (ex : ERP Vendeur Guadeloupe)');
    if (!form.scopes.length) return toast.error('Sélectionnez au moins un scope');
    const r = await fetch(`${API}/admin/api-keys`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setNewKey(d.api_key);
    setForm({ name: '', partner_email: '', scopes: ['catalog:read'], monthly_quota: 10000 });
    toast.success('Clé API générée — copiez-la maintenant, elle ne sera plus affichée');
    load();
  };

  const toggle = async (k) => {
    const r = await fetch(`${API}/admin/api-keys/${k.id}`, { method: 'PATCH', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(d.is_active ? `${k.name} réactivée` : `${k.name} désactivée`);
    load();
  };

  const revoke = async (k) => {
    if (!window.confirm(`Révoquer définitivement la clé « ${k.name} » ? Le connecteur ERP associé cessera de fonctionner.`)) return;
    const r = await fetch(`${API}/admin/api-keys/${k.id}`, { method: 'DELETE', credentials: 'include' });
    if (!r.ok) return toast.error('Révocation impossible');
    toast.success(`Clé ${k.name} révoquée`);
    load();
  };

  const copyKey = () => { navigator.clipboard.writeText(newKey); toast.success('Clé copiée'); };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="api-keys-panel">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-display text-lg text-white flex items-center gap-2">
          <KeyRound size={16} style={{ color: '#D9B35A' }} /> Clés API — Connecteurs ERP
          <span className="text-sm font-normal text-white/50">({items.length})</span>
        </h3>
        <Link to="/docs-api" target="_blank" className="text-xs text-[#D9B35A] hover:underline inline-flex items-center gap-1.5" data-testid="api-docs-link">
          <BookOpen size={13} /> Documentation API
        </Link>
      </div>
      <p className="text-xs text-white/45 mb-4">Générez des clés pour que vos partenaires connectent leur ERP à l'API publique <code className="text-[#D9B35A]">/api/public/v1</code> (header <code className="text-[#D9B35A]">X-API-Key</code>).</p>

      {newKey && (
        <div className="mb-4 p-3 rounded-xl border border-emerald-400/30 bg-emerald-400/10" data-testid="new-api-key-box">
          <p className="text-xs text-emerald-300 font-semibold mb-1.5">Nouvelle clé — copiez-la maintenant, elle ne sera plus jamais affichée :</p>
          <div className="flex items-center gap-2">
            <code className="text-xs text-white bg-black/30 px-2 py-1.5 rounded-lg flex-1 break-all" data-testid="new-api-key-value">{newKey}</code>
            <button onClick={copyKey} className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white" data-testid="copy-api-key-btn"><Copy size={14} /></button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nom (ex : ERP Vendeur Guadeloupe)" data-testid="api-key-name-input" className={`${inp} w-64`} />
        <input value={form.partner_email} onChange={(e) => setForm({ ...form, partner_email: e.target.value })}
          placeholder="Email partenaire (optionnel)" className={`${inp} w-56`} />
        <input type="number" min="1" value={form.monthly_quota}
          onChange={(e) => setForm({ ...form, monthly_quota: Number(e.target.value) })}
          title="Quota mensuel de requêtes" data-testid="api-key-quota-input" className={`${inp} w-28`} />
        <button onClick={create} data-testid="api-key-create-btn"
          className="h-10 px-4 rounded-lg text-sm font-semibold text-[#1A092D] inline-flex items-center gap-1.5"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          <Plus size={14} /> Générer une clé
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-5">
        {scopes.map((s) => (
          <button key={s} onClick={() => toggleScope(s)} data-testid={`scope-${s.replace(':', '-')}`}
            className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${form.scopes.includes(s)
              ? 'bg-[#D9B35A]/20 border-[#D9B35A]/50 text-[#E9CF8E]'
              : 'bg-white/[0.04] border-white/15 text-white/50 hover:text-white/80'}`}>
            {SCOPE_LABELS[s] || s}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {items.map((k) => (
          <div key={k.id} className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10" data-testid={`api-key-row-${k.id}`}>
            <div className="flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white font-medium truncate">{k.name}
                {!k.is_active && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300">DÉSACTIVÉE</span>}
              </p>
              <p className="text-[11px] text-white/40 truncate">
                <code>{k.prefix}</code> · {(k.scopes || []).map((s) => SCOPE_LABELS[s] || s).join(', ')} · {k.month_usage || 0}/{k.monthly_quota || 10000} ce mois · {k.requests_count || 0} au total
                {k.last_used_at ? ` · dernier appel ${new Date(k.last_used_at).toLocaleString('fr-FR')}` : ' · jamais utilisée'}
                {k.partner_email && ` · ${k.partner_email}`}
              </p>
            </div>
            <button onClick={() => toggle(k)} title={k.is_active ? 'Désactiver' : 'Réactiver'} data-testid={`api-key-toggle-${k.id}`}
              className="p-2 rounded-lg hover:bg-white/10">
              <Power size={14} className={k.is_active ? 'text-emerald-400' : 'text-white/40'} />
            </button>
            <button onClick={() => revoke(k)} title="Révoquer" data-testid={`api-key-revoke-${k.id}`}
              className="p-2 rounded-lg hover:bg-red-500/15 text-red-400"><Trash2 size={14} /></button>
            </div>
            <WebhookEditor k={k} onSaved={load} />
          </div>
        ))}
        {!items.length && <p className="text-sm text-white/40 py-4 text-center">Aucune clé API — générez la première pour connecter un ERP.</p>}
      </div>
    </div>
  );
};
