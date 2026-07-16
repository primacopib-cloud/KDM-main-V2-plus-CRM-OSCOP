import { useState } from 'react';
import { Package, Plus, RefreshCw, Clock, Flag, ShoppingCart, TrendingUp } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '../ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { toast } from 'sonner';
import { CATEGORIES, UNIT_TYPES, FORMAT_TYPES, TVA_RATES, ZONES } from './vendorConstants';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ===== PRODUCT FORM MODAL =====
export const VendorProductFormModal = ({ isOpen, onClose, onSuccess, vendorId, countries }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    description: '',
    category: 'alimentaire',
    price_ht: '',
    tva_rate: 8.5,
    stock_quantity: '',
    min_order_quantity: 1,
    unit_type: 'unit',
    volume_per_unit: '',
    weight_per_unit: '',
    format_type: 'standard',
    units_per_lot: '',
    lots_per_palette: '',
    country_of_origin: 'FR',
    region_of_origin: '',
    dlc_days: '',
    ean13: '',
    storage_conditions: '',
    brand: '',
    certifications: [],
    available_zones: ['GUADELOUPE'],
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleZoneToggle = (zone) => {
    setFormData(prev => ({
      ...prev,
      available_zones: prev.available_zones.includes(zone)
        ? prev.available_zones.filter(z => z !== zone)
        : [...prev.available_zones, zone]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        price_ht: parseFloat(formData.price_ht),
        tva_rate: parseFloat(formData.tva_rate),
        stock_quantity: parseInt(formData.stock_quantity),
        min_order_quantity: parseInt(formData.min_order_quantity) || 1,
        volume_per_unit: formData.volume_per_unit ? parseFloat(formData.volume_per_unit) : null,
        weight_per_unit: formData.weight_per_unit ? parseFloat(formData.weight_per_unit) : null,
        units_per_lot: formData.units_per_lot ? parseInt(formData.units_per_lot) : null,
        lots_per_palette: formData.lots_per_palette ? parseInt(formData.lots_per_palette) : null,
        dlc_days: formData.dlc_days ? parseInt(formData.dlc_days) : null,
      };

      const response = await fetch(`${API_URL}/api/vendor/products?vendor_id=${vendorId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erreur lors de la soumission');
      }

      const result = await response.json();
      toast.success('Produit soumis !', {
        description: 'Votre produit est en attente de validation par l\'administrateur.'
      });
      onSuccess(result);
      onClose();
    } catch (error) {
      toast.error('Erreur', { description: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5 text-purple-600" />
            Soumettre un nouveau produit
          </DialogTitle>
          <DialogDescription>
            Remplissez les informations du produit. Il sera soumis pour validation par l&apos;administrateur.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-4 h-4" /> Informations de base
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label htmlFor="name">Nom du produit *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Ex: Riz long grain 5kg"
                  required
                  data-testid="product-name"
                />
              </div>
              <div>
                <Label htmlFor="sku">SKU / Référence *</Label>
                <Input
                  id="sku"
                  value={formData.sku}
                  onChange={(e) => handleChange('sku', e.target.value)}
                  placeholder="Ex: ALI-RIZ-001"
                  required
                  data-testid="product-sku"
                />
              </div>
              <div>
                <Label htmlFor="ean13">Code EAN-13</Label>
                <Input
                  id="ean13"
                  value={formData.ean13}
                  onChange={(e) => handleChange('ean13', e.target.value)}
                  placeholder="3700000000000"
                />
              </div>
              <div className="col-span-2">
                <Label htmlFor="description">Description *</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Décrivez votre produit en détail..."
                  rows={3}
                  required
                  data-testid="product-description"
                />
              </div>
              <div>
                <Label htmlFor="category">Catégorie *</Label>
                <Select value={formData.category} onValueChange={(v) => handleChange('category', v)}>
                  <SelectTrigger data-testid="product-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="brand">Marque</Label>
                <Input
                  id="brand"
                  value={formData.brand}
                  onChange={(e) => handleChange('brand', e.target.value)}
                  placeholder="Ex: Ma Marque"
                />
              </div>
            </div>
          </div>

          {/* Pricing */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> Tarification
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="price_ht">Prix HT (€) *</Label>
                <Input
                  id="price_ht"
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.price_ht}
                  onChange={(e) => handleChange('price_ht', e.target.value)}
                  placeholder="0.00"
                  required
                  data-testid="product-price"
                />
              </div>
              <div>
                <Label htmlFor="tva_rate">Taux TVA *</Label>
                <Select value={String(formData.tva_rate)} onValueChange={(v) => handleChange('tva_rate', parseFloat(v))}>
                  <SelectTrigger data-testid="product-tva">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TVA_RATES.map(t => (
                      <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Prix TTC (calculé)</Label>
                <div className="h-10 px-3 py-2 border rounded-md bg-gray-50 text-gray-700 font-mono">
                  {formData.price_ht 
                    ? (parseFloat(formData.price_ht) * (1 + formData.tva_rate / 100)).toFixed(2) + ' €'
                    : '—'
                  }
                </div>
              </div>
            </div>
          </div>

          {/* Stock & Volume */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <ShoppingCart className="w-4 h-4" /> Stock & Format
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="stock_quantity">Quantité en stock *</Label>
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
                <Label htmlFor="min_order_quantity">Quantité min. commande</Label>
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
                <Label htmlFor="unit_type">Unité de vente</Label>
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
                <Label htmlFor="format_type">Format / Conditionnement</Label>
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
                <Label htmlFor="volume_per_unit">Volume (L)</Label>
                <Input
                  id="volume_per_unit"
                  type="number"
                  step="0.01"
                  value={formData.volume_per_unit}
                  onChange={(e) => handleChange('volume_per_unit', e.target.value)}
                  placeholder="Ex: 5"
                />
              </div>
              <div>
                <Label htmlFor="weight_per_unit">Poids (kg)</Label>
                <Input
                  id="weight_per_unit"
                  type="number"
                  step="0.01"
                  value={formData.weight_per_unit}
                  onChange={(e) => handleChange('weight_per_unit', e.target.value)}
                  placeholder="Ex: 5"
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
                <Label htmlFor="country_of_origin">Pays d&apos;origine *</Label>
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
                <Label htmlFor="region_of_origin">Région (optionnel)</Label>
                <Input
                  id="region_of_origin"
                  value={formData.region_of_origin}
                  onChange={(e) => handleChange('region_of_origin', e.target.value)}
                  placeholder="Ex: Bretagne"
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
                <Label htmlFor="dlc_days">DLC (jours)</Label>
                <Input
                  id="dlc_days"
                  type="number"
                  min="0"
                  value={formData.dlc_days}
                  onChange={(e) => handleChange('dlc_days', e.target.value)}
                  placeholder="Ex: 365"
                />
              </div>
              <div>
                <Label htmlFor="storage_conditions">Conditions de stockage</Label>
                <Input
                  id="storage_conditions"
                  value={formData.storage_conditions}
                  onChange={(e) => handleChange('storage_conditions', e.target.value)}
                  placeholder="Ex: Conserver au frais"
                />
              </div>
            </div>
          </div>

          {/* Zones */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              Zones de disponibilité *
            </h3>
            <div className="flex flex-wrap gap-2">
              {ZONES.map(zone => (
                <Button
                  key={zone}
                  type="button"
                  variant={formData.available_zones.includes(zone) ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleZoneToggle(zone)}
                  className={formData.available_zones.includes(zone) ? "bg-purple-600 hover:bg-purple-700" : ""}
                >
                  {zone}
                </Button>
              ))}
            </div>
            {formData.available_zones.length === 0 && (
              <p className="text-sm text-red-500">Sélectionnez au moins une zone</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button 
              type="submit" 
              disabled={loading || formData.available_zones.length === 0}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="submit-product"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Soumettre pour validation
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
