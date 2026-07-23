import i18n from '@/i18n';
import { useState, useEffect } from 'react';
import { Package, Plus, RefreshCw, Clock, Flag, ShoppingCart, TrendingUp, Save, Lock } from 'lucide-react';
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
import { ProductPhotoUploader, uploadProductPhotos } from './ProductPhotoUploader';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const EMPTY_FORM = {
  name: '', sku: '', description: '', category: 'alimentaire', price_ht: '', tva_rate: 8.5,
  stock_quantity: '', min_order_quantity: 1, unit_type: 'unit', volume_per_unit: '',
  weight_per_unit: '', format_type: 'standard', units_per_lot: '', lots_per_palette: '',
  country_of_origin: 'FR', region_of_origin: '', dlc_days: '', ean13: '',
  storage_conditions: '', brand: '', certifications: [], available_zones: ['GUADELOUPE'],
};

// ===== PRODUCT FORM MODAL (création + édition) =====
export const VendorProductFormModal = ({ isOpen, onClose, onSuccess, vendorId, countries, editProduct = null }) => {
  const isEdit = Boolean(editProduct);
  const [loading, setLoading] = useState(false);
  const [photos, setPhotos] = useState([]);
  const [categories, setCategories] = useState(CATEGORIES);
  const [tvaRates, setTvaRates] = useState(TVA_RATES);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [aiLoading, setAiLoading] = useState(false);
  const [allowance, setAllowance] = useState(null);

  useEffect(() => {
    if (!isOpen || !vendorId) return;
    fetch(`${API_URL}/api/vendor/zone-allowance/${vendorId}`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setAllowance(d);
        if (!editProduct && d.codes?.length) {
          setFormData((prev) => {
            const kept = prev.available_zones.filter((z) => d.codes.includes(z));
            return { ...prev, available_zones: kept.length ? kept : [d.codes[0]] };
          });
        }
      })
      .catch(() => {});
  }, [isOpen, vendorId, editProduct]);

  const isZoneLocked = (zone) => Boolean(allowance?.codes?.length) && !allowance.codes.includes(zone);

  const generateAICopy = async () => {
    if (!formData.name.trim()) return toast.error("Renseignez d'abord le nom du produit");
    setAiLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/vendor/ai/product-copy`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formData.name, category: formData.category, brand: formData.brand, region: formData.region_of_origin }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Génération impossible');
      setFormData((prev) => ({ ...prev, description: d.description }));
      if (d.price_advice) toast.info(`VENT'IA — Conseil prix : ${d.price_advice}`, { duration: 9000 });
      toast.success("Description générée par VENT'IA");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  const [aiImgLoading, setAiImgLoading] = useState(false);
  const generateAIImage = async () => {
    if (!formData.name.trim()) return toast.error("Renseignez d'abord le nom du produit");
    setAiImgLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/vendor/ai/product-image`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formData.name, category: formData.category, brand: formData.brand, region: formData.region_of_origin }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Génération impossible');
      const imgUrl = `${API_URL}${d.image_url}`;
      const blob = await (await fetch(imgUrl)).blob();
      const file = new File([blob], 'visuel-ventia.png', { type: 'image/png' });
      setPhotos((prev) => [...prev, { file, preview: URL.createObjectURL(file), isPrimary: prev.length === 0 }]);
      toast.success("Visuel généré par VENT'IA — ajouté aux photos du produit");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setAiImgLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    setPhotos([]);
    setFormData(editProduct ? {
      ...EMPTY_FORM,
      ...Object.fromEntries(Object.entries(editProduct).filter(([k]) => k in EMPTY_FORM).map(([k, v]) => [k, v ?? EMPTY_FORM[k]])),
    } : EMPTY_FORM);
  }, [isOpen, editProduct]);

  // Taxonomie dynamique gérée par le super admin (fallback constantes)
  useEffect(() => {
    fetch(`${API_URL}/api/taxonomy/categories`).then((r) => r.ok && r.json()).then((d) => {
      if (d?.categories?.length) setCategories(d.categories.map((c) => ({ value: c.value, label: c.label })));
    }).catch(() => {});
    fetch(`${API_URL}/api/taxonomy/tva-rates`).then((r) => r.ok && r.json()).then((d) => {
      if (d?.rates?.length) setTvaRates(d.rates.map((r) => ({ value: r.value, label: r.label })));
    }).catch(() => {});
  }, [isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleZoneToggle = (zone) => {
    if (isZoneLocked(zone)) {
      toast.info('Zone non incluse dans votre abonnement', {
        description: 'Ajoutez une zone additionnelle depuis votre portefeuille (Wallet) pour étendre votre couverture.',
      });
      return;
    }
    const selected = formData.available_zones.includes(zone);
    if (!selected && allowance?.count && formData.available_zones.length >= allowance.count) {
      toast.error(`Votre abonnement autorise ${allowance.count} zone(s) maximum`, {
        description: 'Ajoutez une zone additionnelle depuis votre portefeuille pour en sélectionner davantage.',
      });
      return;
    }
    setFormData(prev => ({
      ...prev,
      available_zones: selected
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

      let productId;
      if (isEdit) {
        const editPayload = {
          name: payload.name, description: payload.description, price_ht: payload.price_ht,
          stock_quantity: payload.stock_quantity, min_order_quantity: payload.min_order_quantity,
          available_zones: payload.available_zones, dlc_days: payload.dlc_days,
        };
        const response = await fetch(`${API_URL}/api/vendor/products/${vendorId}/${editProduct.id}`, {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(editPayload),
        });
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Erreur lors de la modification');
        }
        productId = editProduct.id;
      } else {
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
        productId = result.product_id || result.id || result.product?.id;
      }

      if (photos.length > 0 && productId) {
        const uploaded = await uploadProductPhotos(API_URL, vendorId, productId, photos);
        if (uploaded < photos.length) toast.error(`${photos.length - uploaded} photo(s) non téléversée(s)`);
      }

      toast.success(isEdit ? 'Produit modifié' : i18n.t('adm.produit_soumis'), {
        description: isEdit ? 'Vos modifications ont été enregistrées.' : 'Votre produit est en attente de validation par l\'administrateur.'
      });
      onSuccess();
      onClose();
    } catch (error) {
      toast.error(i18n.t('adm.erreur'), { description: error.message });
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
            {isEdit ? `Modifier : ${editProduct.name}` : 'Soumettre un nouveau produit'}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Champs modifiables : nom, description, prix HT, stock, quantité min., zones et DLC. Les autres champs sont figés après soumission.'
              : 'Remplissez les informations du produit. Il sera soumis pour validation par l\u2019administrateur.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Photos */}
          <ProductPhotoUploader photos={photos} setPhotos={setPhotos} />
          {photos.length === 0 && (
            <Button type="button" variant="outline" size="sm" onClick={generateAIImage} disabled={aiImgLoading}
              className="mt-1 h-8 px-3 text-xs" data-testid="ventia-image-btn">
              {aiImgLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <TrendingUp className="w-3 h-3 mr-1" />}
              Pas de photo ? Générer un visuel IA (VENT'IA)
            </Button>
          )}

          {/* Basic Info */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-4 h-4" /> Informations de base
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label htmlFor="name">{i18n.t('adm.nom_du_produit_2')}</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder={i18n.t('adm.ex_riz_long_grain_5kg')}
                  required
                  data-testid="product-name"
                />
              </div>
              <div>
                <Label htmlFor="sku">{i18n.t('adm.sku_reference')}</Label>
                <Input
                  id="sku"
                  value={formData.sku}
                  onChange={(e) => handleChange('sku', e.target.value)}
                  placeholder={i18n.t('adm.ex_ali_riz_001')}
                  required
                  data-testid="product-sku"
                />
              </div>
              <div>
                <Label htmlFor="ean13">{i18n.t('adm.code_ean_13')}</Label>
                <Input
                  id="ean13"
                  value={formData.ean13}
                  onChange={(e) => handleChange('ean13', e.target.value)}
                  placeholder="3700000000000"
                />
              </div>
              <div className="col-span-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="description">{i18n.t('adm.description_2')}</Label>
                  <Button type="button" variant="outline" size="sm" onClick={generateAICopy} disabled={aiLoading}
                    className="h-7 px-2 text-xs" data-testid="ventia-generate-btn">
                    {aiLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <TrendingUp className="w-3 h-3 mr-1" />}
                    Générer par VENT'IA
                  </Button>
                </div>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder={i18n.t('adm.decrivez_votre_produit_en_detail')}
                  rows={3}
                  required
                  data-testid="product-description"
                />
              </div>
              <div>
                <Label htmlFor="category">{i18n.t('adm.categorie_2')}</Label>
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
                <Label htmlFor="brand">{i18n.t('adm.marque')}</Label>
                <Input
                  id="brand"
                  value={formData.brand}
                  onChange={(e) => handleChange('brand', e.target.value)}
                  placeholder={i18n.t('adm.ex_ma_marque')}
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
                <Label htmlFor="price_ht">{i18n.t('adm.prix_ht_2')}</Label>
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
                <Label htmlFor="tva_rate">{i18n.t('adm.taux_tva')}</Label>
                <Select value={String(formData.tva_rate)} onValueChange={(v) => handleChange('tva_rate', parseFloat(v))}>
                  <SelectTrigger data-testid="product-tva">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {tvaRates.map(t => (
                      <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>{i18n.t('adm.prix_ttc_calcule')}</Label>
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

          {/* Zones */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              {i18n.t('adm.zones_disponibilite_req')}
            </h3>
            {allowance && (
              <p className="text-xs text-gray-600" data-testid="zone-allowance-info">
                {formData.available_zones.length} / {allowance.count} zone(s) incluse(s) dans votre abonnement
                {' — '}
                <a href="/wallet" className="text-purple-600 underline" data-testid="zone-allowance-wallet-link">
                  ajouter une zone additionnelle
                </a>
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {ZONES.map(zone => {
                const locked = isZoneLocked(zone);
                return (
                  <Button
                    key={zone}
                    type="button"
                    variant={formData.available_zones.includes(zone) ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleZoneToggle(zone)}
                    data-testid={`product-zone-${zone}`}
                    className={
                      formData.available_zones.includes(zone)
                        ? "bg-purple-600 hover:bg-purple-700"
                        : locked ? "opacity-50 border-dashed" : ""
                    }
                  >
                    {locked && <Lock className="w-3 h-3 mr-1" />}
                    {zone}{locked ? ' — non incluse' : ''}
                  </Button>
                );
              })}
            </div>
            {formData.available_zones.length === 0 && (
              <p className="text-sm text-red-500">{i18n.t('adm.selectionnez_au_moins_une_zone')}</p>
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
              ) : isEdit ? (
                <Save className="w-4 h-4 mr-2" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              {isEdit ? 'Enregistrer les modifications' : 'Soumettre pour validation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
