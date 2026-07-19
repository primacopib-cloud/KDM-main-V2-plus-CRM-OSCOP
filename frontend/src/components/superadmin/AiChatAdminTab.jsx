import { useEffect, useState } from 'react';
import { Sparkles, Save, Loader2, Coins, Users, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Switch } from '../ui/switch';

const MODELS = [
  { provider: 'openai', model: 'gpt-5.4', label: 'GPT-5.4 (recommandé)' },
  { provider: 'openai', model: 'gpt-5.4-mini', label: 'GPT-5.4 Mini (économique)' },
  { provider: 'anthropic', model: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
  { provider: 'gemini', model: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro' },
];

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[11px] uppercase tracking-wider text-white/50">{label}</span>
    <div className="mt-1">{children}</div>
  </label>
);

const inputCls = 'w-full rounded-lg px-3 py-2 text-sm text-white bg-white/[0.06] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

export const AiChatAdminTab = () => {
  const [s, setS] = useState(null);
  const [stats, setStats] = useState(null);
  const [saving, setSaving] = useState(false);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  useEffect(() => {
    fetch(`${API}/ai-chat/admin/settings`, opts).then((r) => r.json()).then(setS);
    fetch(`${API}/ai-chat/admin/stats`, opts).then((r) => r.json()).then(setStats);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/ai-chat/admin/settings`, {
        method: 'PUT', ...opts,
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: s.enabled,
          provider: s.provider,
          model: s.model,
          assistant_name: s.assistant_name,
          system_prompt: s.system_prompt,
          block_size_chars: Number(s.block_size_chars),
          credits_per_block: Number(s.credits_per_block),
          min_cost_uc: Number(s.min_cost_uc),
          max_question_chars: Number(s.max_question_chars),
        }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || 'Sauvegarde impossible');
      }
      setS(await r.json());
      toast.success('Paramètres du chat IA enregistrés');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!s) return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>;

  const exampleCost = Math.max(Number(s.min_cost_uc) || 0, Math.ceil(50 / Math.max(1, Number(s.block_size_chars) || 50)) * (Number(s.credits_per_block) || 0));

  return (
    <div className="space-y-5" data-testid="ai-chat-admin-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#D9B35A]" /> Chat IA payant — {s.assistant_name}
          </h2>
          <p className="text-white/55 text-sm mt-1">Conditions de crédits et paramètres gérés ici (Super Admin & Admin).</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/60">{s.enabled ? 'Activé' : 'Désactivé'}</span>
          <Switch checked={s.enabled} onCheckedChange={(v) => setS({ ...s, enabled: v })} data-testid="ai-chat-enabled-switch" />
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-3 max-w-xl" data-testid="ai-chat-stats">
          {[
            { label: 'Questions posées', value: stats.total_questions, Icon: MessageSquare },
            { label: 'Crédits consommés', value: `${stats.total_credits_uc} UC`, Icon: Coins },
            { label: 'Utilisateurs', value: stats.unique_users, Icon: Users },
          ].map(({ label, value, Icon }) => (
            <div key={label} className="rounded-xl px-4 py-3 bg-white/[0.05] border border-white/10">
              <p className="text-xl font-bold text-[#E9CF8E] flex items-center gap-2"><Icon className="w-4 h-4 text-[#D9B35A]" />{value}</p>
              <p className="text-[11px] text-white/50 uppercase tracking-wide mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="glass-panel-soft rounded-[18px] p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Taille de bloc (caractères)">
          <input type="number" min="1" value={s.block_size_chars} data-testid="ai-chat-block-size-input"
            onChange={(e) => setS({ ...s, block_size_chars: e.target.value })} className={inputCls} />
        </Field>
        <Field label="Crédits par bloc (UC)">
          <input type="number" min="0" value={s.credits_per_block} data-testid="ai-chat-credits-per-block-input"
            onChange={(e) => setS({ ...s, credits_per_block: e.target.value })} className={inputCls} />
        </Field>
        <Field label="Coût minimum par question (UC)">
          <input type="number" min="0" value={s.min_cost_uc}
            onChange={(e) => setS({ ...s, min_cost_uc: e.target.value })} className={inputCls} />
        </Field>
        <Field label="Longueur max. d'une question (caractères)">
          <input type="number" min="50" value={s.max_question_chars}
            onChange={(e) => setS({ ...s, max_question_chars: e.target.value })} className={inputCls} />
        </Field>
        <Field label="Nom de l'assistant">
          <input value={s.assistant_name} onChange={(e) => setS({ ...s, assistant_name: e.target.value })} className={inputCls} />
        </Field>
        <Field label="Modèle IA">
          <select
            value={`${s.provider}|${s.model}`}
            onChange={(e) => { const [provider, model] = e.target.value.split('|'); setS({ ...s, provider, model }); }}
            className={inputCls}
            data-testid="ai-chat-model-select"
          >
            {MODELS.map((m) => (
              <option key={m.model} value={`${m.provider}|${m.model}`} style={{ color: '#1F0A33' }}>{m.label}</option>
            ))}
          </select>
        </Field>
        <div className="md:col-span-2">
          <Field label="Instructions système (personnalité de l'assistant)">
            <textarea rows={4} value={s.system_prompt}
              onChange={(e) => setS({ ...s, system_prompt: e.target.value })} className={inputCls} />
          </Field>
        </div>
        <div className="md:col-span-2 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-[#E9CF8E]" data-testid="ai-chat-example-cost">
            Exemple : une question de 50 caractères coûte <b>{exampleCost} crédit(s)</b>.
          </p>
          <button type="button" onClick={save} disabled={saving} data-testid="ai-chat-save-settings-btn"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Enregistrer
          </button>
        </div>
      </div>

      {stats && stats.recent?.length > 0 && (
        <div className="glass-panel-soft rounded-[18px] p-4">
          <h3 className="text-sm font-semibold text-[#D9B35A] mb-3">Dernières questions</h3>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {stats.recent.map((r) => (
              <div key={`${r.created_at}-${r.user_email}`} className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-white/[0.04] text-xs">
                <span className="text-white/80 truncate">{r.content}</span>
                <span className="text-white/45 shrink-0">{r.user_email}</span>
                <span className="text-[#E9CF8E] font-semibold shrink-0">−{r.cost_uc} UC</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
