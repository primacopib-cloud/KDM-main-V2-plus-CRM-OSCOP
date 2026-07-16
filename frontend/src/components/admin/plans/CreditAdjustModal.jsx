import { useEffect, useState } from 'react';
import { X, Coins, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Label } from '../../ui/label';

export const CreditAdjustModal = ({ open, onClose, onSave, user }) => {
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [reference, setReference] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setAmount('');
      setReason('');
      setReference('');
    }
  }, [open]);

  if (!open || !user) return null;

  const handleSave = async () => {
    const amt = parseInt(amount);
    if (!amt || !reason) {
      toast.error('Montant et raison sont requis');
      return;
    }
    setSaving(true);
    try {
      await onSave({ amount: amt, reason, reference: reference || null });
      onClose();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\'ajustement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      data-testid="credit-adjust-modal"
    >
      <div
        className="rounded-2xl max-w-md w-full"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-lg font-bold text-white">Ajuster crédits</h2>
          <button onClick={onClose} className="text-white/60 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div
            className="p-3 rounded-lg"
            style={{ background: 'rgba(217,179,90,0.08)' }}
          >
            <div className="text-sm text-white/70">Utilisateur</div>
            <div className="text-white font-medium">{user.email}</div>
            <div className="text-xs text-white/50">
              {user.company_name || '—'} · Solde actuel:{' '}
              <span className="text-[#D9B35A] font-bold">
                {user.credits_balance} crédits
              </span>
            </div>
          </div>

          <div>
            <Label className="text-white/80">
              Montant (positif = ajout, négatif = déduction)
            </Label>
            <Input
              data-testid="credit-amount-input"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="ex. 100 ou -50"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Raison</Label>
            <Input
              data-testid="credit-reason-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="ex. Bonus fidélité"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Référence (optionnel)</Label>
            <Input
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="ex. Facture #2025-001"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button variant="ghost" onClick={onClose} className="text-white/70">
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="credit-adjust-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Coins className="w-4 h-4 mr-2" />
            )}
            Appliquer
          </Button>
        </div>
      </div>
    </div>
  );
};
