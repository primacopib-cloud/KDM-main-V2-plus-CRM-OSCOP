import i18n from '@/i18n';
import { useState } from 'react';
import { toast } from 'sonner';
import { Search, UserPlus, Loader2, Copy, CheckCircle2, Mail, X } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const inputCls = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 w-full';

export const RoleSelect = ({ value, onChange, roles, testId }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testId} className={inputCls}>
    <option value="">{i18n.t('adm.team_role')}…</option>
    {roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
  </select>
);

export const GrantRoleForm = ({ roles, onDone }) => {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [role, setRole] = useState('');
  const [busy, setBusy] = useState(false);

  const search = async (value) => {
    setQ(value);
    setSelected(null);
    if (value.length < 2) { setResults([]); return; }
    const r = await fetch(`${API}/admin/team/search?q=${encodeURIComponent(value)}`, { credentials: 'include' });
    if (r.ok) setResults((await r.json()).users || []);
  };

  const grant = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/admin/team/grant`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: selected.id, role }),
      });
      const data = await r.json();
      if (r.ok) {
        toast.success(i18n.t('adm.team_granted_ok'));
        setQ(''); setResults([]); setSelected(null); setRole('');
        onDone();
      } else {
        toast.error(typeof data.detail === 'string' ? data.detail : 'ERROR');
      }
    } finally { setBusy(false); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="team-grant-form">
      <h3 className="font-display text-lg mb-3 text-white">{i18n.t('adm.team_grant_title')}</h3>
      <div className="relative mb-3">
        <Search size={14} className="absolute left-3 top-3 opacity-40" />
        <input
          value={selected ? `${selected.contact_name || ''} — ${selected.email}` : q}
          onChange={(e) => search(e.target.value)}
          placeholder={i18n.t('adm.team_search_placeholder')}
          data-testid="team-search-input"
          className={`${inputCls} pl-9`}
        />
        {results.length > 0 && !selected && (
          <div className="absolute z-10 left-0 right-0 mt-1 rounded-lg shadow-xl border border-white/15 max-h-52 overflow-y-auto" style={{ background: '#2A1045' }}>
            {results.map((u) => (
              <button
                key={u.id} type="button"
                onClick={() => { setSelected(u); setResults([]); }}
                data-testid={`team-search-result-${u.id}`}
                className="w-full text-left px-3 py-2 text-sm hover:bg-[#D9B35A]/15 text-white"
              >
                <span className="font-medium">{u.contact_name || u.email}</span>
                <span className="opacity-50 text-xs block">{u.email} · {u.role || '—'}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="flex gap-3">
        <RoleSelect value={role} onChange={setRole} roles={roles} testId="team-grant-role-select" />
        <button
          type="button" onClick={grant} disabled={!selected || !role || busy}
          data-testid="team-grant-btn"
          className="btn-gold h-10 px-5 rounded-lg text-sm font-semibold shrink-0 inline-flex items-center gap-2 disabled:opacity-40"
        >
          {busy && <Loader2 size={14} className="animate-spin" />}
          {i18n.t('adm.team_grant_btn')}
        </button>
      </div>
    </div>
  );
};

export const CreateMemberForm = ({ roles, onDone }) => {
  const [form, setForm] = useState({ contact_name: '', email: '', role: '' });
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);

  const create = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/admin/team/create`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await r.json();
      if (r.ok) {
        setCreated(data);
        setForm({ contact_name: '', email: '', role: '' });
        onDone();
      } else {
        toast.error(typeof data.detail === 'string' ? data.detail : 'ERROR');
      }
    } finally { setBusy(false); }
  };

  const copyPassword = () => {
    navigator.clipboard.writeText(created.temp_password);
    toast.success(i18n.t('adm.team_copied'));
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="team-create-form">
      <h3 className="font-display text-lg mb-3 text-white">{i18n.t('adm.team_create_title')}</h3>
      <div className="grid gap-3">
        <input value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
          placeholder={i18n.t('adm.team_name')} data-testid="team-create-name" className={inputCls} />
        <input value={form.email} type="email" onChange={(e) => setForm({ ...form, email: e.target.value })}
          placeholder={i18n.t('adm.team_email')} data-testid="team-create-email" className={inputCls} />
        <RoleSelect value={form.role} onChange={(v) => setForm({ ...form, role: v })} roles={roles} testId="team-create-role-select" />
        <button
          type="button" onClick={create}
          disabled={!form.contact_name || !form.email || !form.role || busy}
          data-testid="team-create-btn"
          className="btn-gold h-10 px-5 rounded-lg text-sm font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-40"
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
          {i18n.t('adm.team_create_btn')}
        </button>
      </div>

      {created && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="team-created-modal">
          <div className="rounded-[20px] p-6 max-w-md w-full bg-white" style={{ boxShadow: '0 24px 64px rgba(76,42,110,0.3)' }}>
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-display text-lg text-white flex items-center gap-2">
                <CheckCircle2 size={18} style={{ color: '#6FA82E' }} /> {i18n.t('adm.team_created_ok')}
              </h4>
              <button type="button" onClick={() => setCreated(null)} data-testid="team-created-close" className="opacity-50 hover:opacity-100 p-1"><X size={16} /></button>
            </div>
            <p className="text-sm text-white mb-1">{created.user.contact_name} — {created.user.email}</p>
            <p className="text-xs opacity-60 mb-3">{i18n.t('adm.team_temp_password')} :</p>
            <div className="flex items-center gap-2 mb-3">
              <code data-testid="team-temp-password" className="flex-1 px-3 py-2 rounded-lg bg-white/10 text-sm font-mono text-white">{created.temp_password}</code>
              <button type="button" onClick={copyPassword} data-testid="team-copy-password" className="btn-ghost h-9 px-3 rounded-lg inline-flex items-center gap-1.5 text-xs">
                <Copy size={12} /> {i18n.t('adm.team_copy')}
              </button>
            </div>
            <p className="text-xs flex items-center gap-1.5" style={{ color: created.email_sent ? '#6FA82E' : '#E64432' }} data-testid="team-email-status">
              <Mail size={12} /> {created.email_sent ? i18n.t('adm.team_email_sent') : i18n.t('adm.team_email_not_sent')}
            </p>
            <p className="text-[11px] opacity-50 mt-3">{i18n.t('adm.team_temp_password_note')}</p>
          </div>
        </div>
      )}
    </div>
  );
};
