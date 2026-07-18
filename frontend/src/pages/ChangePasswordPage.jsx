import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { KeyRound, Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Field = ({ label, value, onChange, show, toggle, testId }) => (
  <div>
    <label className="text-xs uppercase tracking-wider opacity-60 block mb-1.5">{label}</label>
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testId}
        className="h-11 w-full px-3 pr-10 rounded-lg bg-white/60 border border-black/10 text-sm text-[#1F2A3A]"
        autoComplete="new-password"
      />
      <button type="button" onClick={toggle} className="absolute right-3 top-3 opacity-40 hover:opacity-80" tabIndex={-1}>
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  </div>
);

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.next.length < 8) { toast.error('Le nouveau mot de passe doit contenir au moins 8 caractères'); return; }
    if (form.next !== form.confirm) { toast.error('Les deux mots de passe ne correspondent pas'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/auth/change-password`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: form.current, new_password: form.next }),
      });
      const data = await r.json();
      if (!r.ok) { toast.error(typeof data.detail === 'string' ? data.detail : 'Erreur'); return; }
      const stored = JSON.parse(localStorage.getItem('user') || '{}');
      localStorage.setItem('user', JSON.stringify({ ...stored, must_change_password: false }));
      toast.success('Mot de passe modifié avec succès');
      navigate('/dashboard');
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-5 py-12" data-testid="change-password-page">
      <div className="glass-panel-soft rounded-[20px] p-8 max-w-md w-full">
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4"
          style={{ background: '#D9B35A22', border: '1px solid #D9B35A66' }}>
          <KeyRound className="w-6 h-6" style={{ color: '#B8860B' }} />
        </div>
        <h1 className="font-display text-2xl text-[#1F2A3A] mb-1">Choisissez votre mot de passe</h1>
        <p className="text-sm opacity-60 mb-6">
          Votre mot de passe temporaire doit être remplacé avant d&apos;accéder à la plateforme.
        </p>

        <form onSubmit={submit} className="space-y-4">
          <Field label="Mot de passe temporaire" value={form.current}
            onChange={(v) => setForm({ ...form, current: v })}
            show={show} toggle={() => setShow(!show)} testId="change-pwd-current" />
          <Field label="Nouveau mot de passe (min. 8 caractères)" value={form.next}
            onChange={(v) => setForm({ ...form, next: v })}
            show={show} toggle={() => setShow(!show)} testId="change-pwd-new" />
          <Field label="Confirmer le nouveau mot de passe" value={form.confirm}
            onChange={(v) => setForm({ ...form, confirm: v })}
            show={show} toggle={() => setShow(!show)} testId="change-pwd-confirm" />

          <button
            type="submit" disabled={busy || !form.current || !form.next || !form.confirm}
            data-testid="change-pwd-submit"
            className="btn-gold h-11 w-full rounded-lg text-sm font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-40"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
            Valider mon nouveau mot de passe
          </button>
        </form>
      </div>
    </div>
  );
}
