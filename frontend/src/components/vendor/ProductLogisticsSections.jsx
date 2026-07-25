import i18n from '@/i18n';
import { Clock, Flag, ShoppingCart } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { UNIT_TYPES, FORMAT_TYPES } from './vendorConstants';

// Sections Stock & Format / Origine / Conservation (formulaire produit vendeur)
export const ProductLogisticsSections = ({ formData, handleChange, countries }) => (
  <>
    {/* Stock & Volume */}
    <div className="space-y-4">
      <h3 className="font-semibold text-gray-900 flex items-center gap-2">
        <ShoppingCart className="w-4 h-4" /> Stock & Format
      </h3>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="stock_quantity">{i18n.t('adm.quantite_en_stock')}</Label>
          <Input
            id="stock_quantity"
            type="number"
            min="0"
            value={formData.stock_quantity}
            onChange={(e) => handleChange('stock_quantity', e.target.value)}
            placeholder="100"
            required
            data-testid="product-stock"
          />
        </div>
        <div>
          <Label htmlFor="min_order_quantity">{i18n.t('adm.quantite_min_commande')}</Label>
          <Input
            id="min_order_quantity"
            type="number"
            min="1"
            value={formData.min_order_quantity}
            onChange={(e) => handleChange('min_order_quantity', e.target.value)}
            placeholder="1"
          />
        </div>
        <div>
          <Label htmlFor="unit_type">{i18n.t('adm.unite_de_vente')}</Label>
          <Select value={formData.unit_type} onValueChange={(v) => handleChange('unit_type', v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {UNIT_TYPES.map(u => (
                <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="format_type">{i18n.t('adm.format_conditionnement')}</Label>
          <Select value={formData.format_type} onValueChange={(v) => handleChange('format_type', v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FORMAT_TYPES.map(f => (
                <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="volume_per_unit">{i18n.t('adm.volume_l')}</Label>
          <Input
            id="volume_per_unit"
            type="number"
            step="0.01"
            value={formData.volume_per_unit}
            onChange={(e) => handleChange('volume_per_unit', e.target.value)}
            placeholder={i18n.t('adm.ex_5')}
          />
        </div>
        <div>
          <Label htmlFor="weight_per_unit">{i18n.t('adm.poids_kg')}</Label>
          <Input
            id="weight_per_unit"
            type="number"
            step="0.01"
            value={formData.weight_per_unit}
            onChange={(e) => handleChange('weight_per_unit', e.target.value)}
            placeholder={i18n.t('adm.ex_5')}
          />
        </div>
      </div>
    </div>

    {/* Origin */}
    <div className="space-y-4">
      <h3 className="font-semibold text-gray-900 flex items-center gap-2">
        <Flag className="w-4 h-4" /> Origine
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="country_of_origin">{i18n.t('adm.pays_d_origine')}</Label>
          <Select value={formData.country_of_origin} onValueChange={(v) => handleChange('country_of_origin', v)}>
            <SelectTrigger data-testid="product-origin">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {countries.map(c => (
                <SelectItem key={c.code} value={c.code}>
                  {c.flag} {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="region_of_origin">{i18n.t('adm.region_optionnel')}</Label>
          <Input
            id="region_of_origin"
            value={formData.region_of_origin}
            onChange={(e) => handleChange('region_of_origin', e.target.value)}
            placeholder={i18n.t('adm.ex_bretagne')}
          />
        </div>
      </div>
    </div>

    {/* DLC & Storage */}
    <div className="space-y-4">
      <h3 className="font-semibold text-gray-900 flex items-center gap-2">
        <Clock className="w-4 h-4" /> Conservation
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="dlc_days">{i18n.t('adm.dlc_jours')}</Label>
          <Input
            id="dlc_days"
            type="number"
            min="0"
            value={formData.dlc_days}
            onChange={(e) => handleChange('dlc_days', e.target.value)}
            placeholder={i18n.t('adm.ex_365')}
          />
        </div>
        <div>
          <Label htmlFor="storage_conditions">{i18n.t('adm.conditions_de_stockage')}</Label>
          <Input
            id="storage_conditions"
            value={formData.storage_conditions}
            onChange={(e) => handleChange('storage_conditions', e.target.value)}
            placeholder={i18n.t('adm.ex_conserver_au_frais')}
          />
        </div>
      </div>
    </div>
  </>
);
