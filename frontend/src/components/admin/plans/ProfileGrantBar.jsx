import { useState } from 'react';
import { toast } from 'sonner';
import { Users, Coins, Loader2 } from 'lucide-react';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { adminPlansAPI } from '../../../services/api';

const PROFILES = [
  { value: 'vendor', label: 'Vendeurs' },
  { value: 'buyer', label: 'Acheteurs' },
  { value: 'COOPER', label: 'COOPER' },
  { value: 'GERANT_LOLO_POINT', label: 'Gérants Lolo Point' },
  { value: 'OPERATEUR_POS', label: 'Opérateurs POS' },
  { value: 'TITULAIRE_PASS', label: 'Titulaires PASS' },
];

export const ProfileGrantBar = ({ onDone }) => {
  const [profile, setProfile] = useState('vendor');
  const [amount, setAmount] = useState('');
  const [sending, setSending] = useState(false);

  const grant = async () => {
    const n = parseInt(amount, 10);
    if (!n) { toast.error('Indiquez un montant de crédits'); return; }
    setSending(true);
    try {
      const res = await adminPlansAPI.grantByProfile({ profile, amount: n });
      toast.success(res.message);
      setAmount('');
      onDone?.();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\u2019attribution');
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="rounded-xl p-4 mb-5"
      style={{ background: 'rgba(217,179,90,0.06)', border: '1px solid rgba(217,179,90,0.25)' }}
      data-testid="profile-grant-bar"
    >
      <p className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
        <Users className="w-4 h-4" style={{ color: '#D9B35A' }} /> Attribution de crédits par profil
      </p>
      <p className="text-xs text-white/50 mb-3">
        Crédite en une fois tous les comptes du profil sélectionné (vendeurs, acheteurs, COOPER…).
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <select
          value={profile}
          onChange={(e) => setProfile(e.target.value)}
          data-testid="profile-grant-select"
          className="h-10 px-3 rounded-md bg-white/5 border border-white/10 text-white text-sm"
        >
          {PROFILES.map((p) => (
            <option key={p.value} value={p.value} style={{ color: '#000' }}>{p.label}</option>
          ))}
        </select>
        <Input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Nombre de crédits (ex: 50)"
          data-testid="profile-grant-amount"
          className="bg-white/5 border-white/10 text-white max-w-[220px]"
        />
        <Button
          onClick={grant}
          disabled={sending}
          data-testid="profile-grant-btn"
          style={{ background: '#D9B35A', color: '#070A10' }}
        >
          {sending ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Coins className="w-4 h-4 mr-1" />}
          Attribuer
        </Button>
      </div>
    </div>
  );
};
