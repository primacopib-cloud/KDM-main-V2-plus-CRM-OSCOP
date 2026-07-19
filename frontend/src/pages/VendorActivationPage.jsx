import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { KeyRound, Loader2, Rocket } from 'lucide-react';
import { toast } from 'sonner';
import NavBar from '../components/NavBar';
import { API } from '../services/http';

export default function VendorActivationPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);

  const activate = async (e) => {
    e.preventDefault();
    if (password !== confirm) return toast.error('Les mots de passe ne correspondent pas');
    setBusy(true);
    try {
      const r = await fetch(`${API}/vendor-onboarding/activate`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: params.get('token'), password }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Activation impossible');
      toast.success('Espace activé — bienvenue !');
      setTimeout(() => {
        window.location.href = d.user?.role === 'buyer' ? '/espace-acheteur?bienvenue=1' : '/espace-vendeur?bienvenue=1';
      }, 800);
    } catch (err) { toast.error(err.message); setBusy(false); }
  };

  return (
    <div className="min-h-screen" data-testid="vendor-activation-page">
      <NavBar />
      <div className="max-w-md mx-auto px-4 pt-32 pb-16">
        <div className="glass-panel rounded-[22px] p-8">
          <div className="text-center mb-6">
            <Rocket className="w-10 h-10 mx-auto text-[#D9B35A] mb-3" />
            <h1 className="text-xl font-bold text-white">Activez votre espace vendeur</h1>
            <p className="text-white/55 text-sm mt-1">Choisissez votre mot de passe pour finaliser votre adhésion.</p>
          </div>
          <form onSubmit={activate} className="space-y-4">
            <input type="password" required minLength={8} placeholder="Mot de passe (8 caractères min.)"
              data-testid="activation-password-input"
              className="w-full h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60"
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <input type="password" required placeholder="Confirmez le mot de passe"
              data-testid="activation-confirm-input"
              className="w-full h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60"
              value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            <button type="submit" disabled={busy} data-testid="activation-submit-btn"
              className="w-full py-3 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-bold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />} Activer mon espace
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
