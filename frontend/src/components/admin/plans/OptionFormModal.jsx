import i18n from '@/i18n';
import { useEffect, useState } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Textarea } from '../../ui/textarea';
import { Switch } from '../../ui/switch';
import { Label } from '../../ui/label';

export const EMPTY_OPTION = {
  name: '',
  description: '',
  price_cents: 0,
  period: 'mois',
  credits_included: 0,
  compatible_plans: [],
  active: true,
  sort_order: 0,
};

export const OptionFormModal = ({ open, onClose, onSave, initialData, isEdit, plans }) => {
  const [data, setData] = useState(initialData || EMPTY_OPTION);
  const [priceEur, setPriceEur] = useState(
    ((initialData?.price_cents || 0) / 100).toString()
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setData(initialData || EMPTY_OPTION);
    setPriceEur(((initialData?.price_cents || 0) / 100).toString());
  }, [initialData]);

  if (!open) return null;

  const togglePlan = (planId) => {
    const list = data.compatible_plans || [];
    setData({
      ...data,
      compatible_plans: list.includes(planId)
        ? list.filter((p) => p !== planId)
        : [...list, planId],
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...data,
        price_cents: Math.round(parseFloat(priceEur || 0) * 100),
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
      data-testid="option-form-modal"
    >
      <div
        className="rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto"
        style={{ background: '#0f1623', border: '1px solid rgba(217,179,90,0.3)' }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-xl font-bold text-white">
            {isEdit ? 'Modifier l\'option' : 'Nouvelle option / addon'}
          </h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white"
            data-testid="option-modal-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <Label className="text-white/80">{i18n.t('adm.nom_de_l_option')}</Label>
            <Input
              data-testid="option-name-input"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              placeholder={i18n.t('adm.ex_zone_supplementaire')}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>

          <div>
            <Label className="text-white/80">{i18n.t('adm.description')}</Label>
            <Textarea
              value={data.description || ''}
              onChange={(e) => setData({ ...data, description: e.target.value })}
              className="bg-white/5 border-white/10 text-white"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-white/80">{i18n.t('adm.prix')}</Label>
              <Input
                data-testid="option-price-input"
                type="number"
                step="0.01"
                value={priceEur}
                onChange={(e) => setPriceEur(e.target.value)}
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
            <div>
              <Label className="text-white/80">{i18n.t('adm.periode_2')}</Label>
              <select
                value={data.period}
                onChange={(e) => setData({ ...data, period: e.target.value })}
                className="w-full px-3 py-2 rounded-md bg-white/5 border border-white/10 text-white"
              >
                <option value="mois">{i18n.t('adm.mois')}</option>
                <option value="an">an</option>
                <option value="unique">{i18n.t('adm.unique')}</option>
              </select>
            </div>
            <div>
              <Label className="text-white/80">{i18n.t('adm.credits_inclus')}</Label>
              <Input
                type="number"
                value={data.credits_included}
                onChange={(e) =>
                  setData({ ...data, credits_included: parseInt(e.target.value || 0) })
                }
                className="bg-white/5 border-white/10 text-white"
              />
            </div>
          </div>

          <div>
            <Label className="text-white/80">
              Plans compatibles (vide = tous les plans)
            </Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {(plans || []).map((p) => {
                const checked = (data.compatible_plans || []).includes(p.id);
                return (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => togglePlan(p.id)}
                    className="px-3 py-1.5 rounded-full text-sm transition"
                    style={{
                      background: checked ? '#D9B35A' : 'rgba(255,255,255,0.05)',
                      color: checked ? '#070A10' : 'rgba(255,255,255,0.7)',
                      border: '1px solid rgba(217,179,90,0.3)',
                    }}
                    data-testid={`option-plan-toggle-${p.slug}`}
                  >
                    {p.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <Switch
              checked={data.active}
              onCheckedChange={(v) => setData({ ...data, active: v })}
            />
            <Label className="text-white/80">{i18n.t('adm.active')}</Label>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-white/10">
          <Button
            variant="ghost"
            onClick={onClose}
            className="text-white/70"
            data-testid="option-modal-cancel"
          >
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !data.name}
            data-testid="option-modal-save"
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
