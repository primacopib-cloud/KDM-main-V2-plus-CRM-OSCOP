import { useEffect, useState } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Textarea } from '../../ui/textarea';
import { Switch } from '../../ui/switch';
import { Label } from '../../ui/label';

export const EMPTY_PACK = {
  name: '',
  description: '',
  credits: 100,
  price: 50,
  popular: false,
  active: true,
  sort_order: 0,
};

export const WalletPackFormModal = ({ open, onClose, onSave, initialData, isEdit }) => {
  const [data, setData] = useState(initialData || EMPTY_PACK);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setData(initialData || EMPTY_PACK);
  }, [initialData]);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        ...data,
        credits: parseInt(data.credits || 0, 10),
        price: parseFloat(data.price || 0),
        sort_order: parseInt(data.sort_order || 0, 10),
      });
      onClose();
    } catch (e) {
      toast.error(e.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      data-testid="wallet-pack-form-modal"
    >
      <div
        className="rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto"
        style={{ background: '#221038', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {isEdit ? 'Modifier le pack de crédits' : 'Nouveau pack de crédits'}
          </h2>
          <button onClick={onClose} className="text-white/60 hover:text-white" data-testid="wallet-pack-modal-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <Label className="text-white/80">Nom du pack</Label>
            <Input
              data-testid="wallet-pack-name-input"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              placeholder="Ex : Pack COOPER"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Description</Label>
            <Textarea
              value={data.description || ''}
              onChange={(e) => setData({ ...data, description: e.target.value })}
              className="bg-white/5 border-white/10 text-white"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-white/80">Crédits</Label>
              <Input
                data-testid="wallet-pack-credits-input"
                type="number"
                value={data.credits}
                onChange={(e) => setData({ ...data, credits: e.target.value })}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Prix (€)</Label>
              <Input
                data-testid="wallet-pack-price-input"
                type="number"
                step="0.01"
                value={data.price}
                onChange={(e) => setData({ ...data, price: e.target.value })}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Ordre</Label>
              <Input
                type="number"
                value={data.sort_order}
                onChange={(e) => setData({ ...data, sort_order: e.target.value })}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
          </div>

          <div className="flex items-center gap-6 pt-2">
            <div className="flex items-center gap-2">
              <Switch
                checked={data.popular}
                onCheckedChange={(v) => setData({ ...data, popular: v })}
              />
              <Label className="text-white/80">Populaire</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={data.active}
                onCheckedChange={(v) => setData({ ...data, active: v })}
                data-testid="wallet-pack-active-switch"
              />
              <Label className="text-white/80">Visible (achetable)</Label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button variant="ghost" onClick={onClose} className="text-white/70" data-testid="wallet-pack-modal-cancel">
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !data.name}
            data-testid="wallet-pack-modal-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Enregistrer
          </Button>
        </div>
      </div>
    </div>
  );
};
