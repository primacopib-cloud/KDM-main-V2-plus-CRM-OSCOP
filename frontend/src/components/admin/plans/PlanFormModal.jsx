import { useEffect, useState } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Textarea } from '../../ui/textarea';
import { Switch } from '../../ui/switch';
import { Label } from '../../ui/label';

export const EMPTY_PLAN = {
  name: '',
  description: '',
  price_cents: 0,
  period: 'mois',
  default_credits: 100,
  features: [],
  popular: false,
  active: true,
  sort_order: 0,
  max_zones: 1,
  max_users: 1,
  color: '#D9B35A',
};

export const PlanFormModal = ({ open, onClose, onSave, initialData, isEdit }) => {
  const [data, setData] = useState(initialData || EMPTY_PLAN);
  const [featuresText, setFeaturesText] = useState(
    (initialData?.features || []).join('\n')
  );
  const [saving, setSaving] = useState(false);
  const [priceEur, setPriceEur] = useState(
    ((initialData?.price_cents || 0) / 100).toString()
  );

  useEffect(() => {
    setData(initialData || EMPTY_PLAN);
    setFeaturesText((initialData?.features || []).join('\n'));
    setPriceEur(((initialData?.price_cents || 0) / 100).toString());
  }, [initialData]);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...data,
        price_cents: Math.round(parseFloat(priceEur || 0) * 100),
        features: featuresText
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await onSave(payload);
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
      data-testid="plan-form-modal"
    >
      <div
        className="rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {isEdit ? 'Modifier le plan' : 'Nouveau plan d\'abonnement'}
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white"
            data-testid="plan-modal-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <Label className="text-white/80">Nom du plan</Label>
            <Input
              data-testid="plan-name-input"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              placeholder="ex. ESS PREMIUM"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">Description</Label>
            <Textarea
              data-testid="plan-description-input"
              value={data.description || ''}
              onChange={(e) => setData({ ...data, description: e.target.value })}
              placeholder="Description courte du plan"
              className="bg-white/5 border-white/10 text-white"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white/80">Prix (€)</Label>
              <Input
                data-testid="plan-price-input"
                type="number"
                step="0.01"
                value={priceEur}
                onChange={(e) => setPriceEur(e.target.value)}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Période</Label>
              <select
                data-testid="plan-period-select"
                value={data.period}
                onChange={(e) => setData({ ...data, period: e.target.value })}
                className="w-full px-3 py-2 rounded-md bg-white/5 border border-white/10 text-white"
              >
                <option value="mois">mois</option>
                <option value="an">an</option>
                <option value="unique">unique</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-white/80">Crédits par défaut</Label>
              <Input
                data-testid="plan-credits-input"
                type="number"
                value={data.default_credits}
                onChange={(e) =>
                  setData({ ...data, default_credits: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Zones max</Label>
              <Input
                type="number"
                value={data.max_zones}
                onChange={(e) =>
                  setData({ ...data, max_zones: parseInt(e.target.value || 1) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Utilisateurs max</Label>
              <Input
                type="number"
                value={data.max_users}
                onChange={(e) =>
                  setData({ ...data, max_users: parseInt(e.target.value || 1) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
          </div>

          <div>
            <Label className="text-white/80">Fonctionnalités (une par ligne)</Label>
            <Textarea
              data-testid="plan-features-input"
              value={featuresText}
              onChange={(e) => setFeaturesText(e.target.value)}
              placeholder="Accès catalogue&#10;Crédits inclus&#10;..."
              className="bg-white/5 border-white/10 text-white font-mono text-sm"
              rows={6}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white/80">Ordre d&apos;affichage</Label>
              <Input
                type="number"
                value={data.sort_order}
                onChange={(e) =>
                  setData({ ...data, sort_order: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">Couleur</Label>
              <Input
                type="color"
                value={data.color || '#D9B35A'}
                onChange={(e) => setData({ ...data, color: e.target.value })}
                className="bg-white/5 border-white/10 text-white h-10"
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2">
              <Switch
                data-testid="plan-popular-switch"
                checked={data.popular}
                onCheckedChange={(v) => setData({ ...data, popular: v })}
              />
              <Label className="text-white/80">Plan populaire</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                data-testid="plan-active-switch"
                checked={data.active}
                onCheckedChange={(v) => setData({ ...data, active: v })}
              />
              <Label className="text-white/80">Actif</Label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button
            variant="ghost"
            onClick={onClose}
            data-testid="plan-modal-cancel"
            className="text-white/70"
          >
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !data.name}
            data-testid="plan-modal-save"
            style={{ background: '#D9B35A', color: '#070A10' }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Enregistrer
          </Button>
        </div>
      </div>
    </div>
  );
};
