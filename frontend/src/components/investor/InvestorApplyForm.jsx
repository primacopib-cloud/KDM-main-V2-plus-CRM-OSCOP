import { useState } from 'react';
import { Loader2, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { API, getSessionToken } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export const InvestorApplyForm = () => {
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '', message: '' });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  if (getSessionToken() || sent) {
    return sent ? (
      <p className="text-emerald-300 text-sm mt-8" data-testid="investor-apply-sent">
        Candidature transmise — l'équipe O'SCOP valide chaque compte investisseur et vous contactera.
      </p>
    ) : null;
  }

  const submit = async () => {
    if (!form.name || !form.email || form.password.length < 8) {
      toast.error('Nom, email et mot de passe (8 caractères min.) requis');
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${API}/investor/apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Erreur');
      setSent(true);
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="glass-panel-soft rounded-[22px] p-5 mt-8" data-testid="investor-apply-form">
      <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
        <UserPlus className="w-5 h-5 text-[#D9B35A]" /> Demander un compte investisseur
      </h2>
      <p className="text-white/55 text-xs mb-3">Chaque ouverture de compte est validée individuellement par l'équipe O'SCOP.</p>
      <div className="grid sm:grid-cols-2 gap-2">
        <Input placeholder="Nom / raison sociale" value={form.name} data-testid="apply-name"
          onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-white/5 border-white/15 text-white" />
        <Input placeholder="Email" type="email" value={form.email} data-testid="apply-email"
          onChange={(e) => setForm({ ...form, email: e.target.value })} className="bg-white/5 border-white/15 text-white" />
        <Input placeholder="Mot de passe (8 car. min.)" type="password" value={form.password} data-testid="apply-password"
          onChange={(e) => setForm({ ...form, password: e.target.value })} className="bg-white/5 border-white/15 text-white" />
        <Input placeholder="Téléphone" value={form.phone} data-testid="apply-phone"
          onChange={(e) => setForm({ ...form, phone: e.target.value })} className="bg-white/5 border-white/15 text-white" />
      </div>
      <Button onClick={submit} disabled={busy} data-testid="apply-submit"
        className="mt-3 bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold">
        {busy && <Loader2 className="w-4 h-4 animate-spin mr-2" />} Envoyer ma candidature
      </Button>
    </div>
  );
};
