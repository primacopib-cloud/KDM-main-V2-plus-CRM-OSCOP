import {
  Tag, Info, CheckCircle2, Ruler, Box, Globe,
} from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { TabsContent } from '../ui/tabs';
import { CountryFlag } from './CountryFlag';
import { FormSection, TagInput } from './FormInputs';
import { CATEGORIES, UNITS, TVA_RATES, COUNTRIES, formatPrice } from './constants';

export const BasicTab = ({ formData, handleChange }) => (
            <TabsContent value="basic" className="space-y-4">
              <FormSection title="Identification" icon={Tag}>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">SKU *</Label>
                    <Input
                      value={formData.sku}
                      onChange={(e) => handleChange('sku', e.target.value)}
                      placeholder="REF-001"
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Code EAN-13</Label>
                    <Input
                      value={formData.ean}
                      onChange={(e) => handleChange('ean', e.target.value)}
                      placeholder="3760012345678"
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Réf. fabricant</Label>
                    <Input
                      value={formData.manufacturer_ref}
                      onChange={(e) => handleChange('manufacturer_ref', e.target.value)}
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                  </div>
                </div>
              </FormSection>

              <FormSection title="Informations produit" icon={Info}>
                <div className="space-y-4">
                  <div>
                    <Label className="text-white/70 text-xs">Nom du produit *</Label>
                    <Input
                      value={formData.name}
                      onChange={(e) => handleChange('name', e.target.value)}
                      placeholder="Nom du produit"
                      className="mt-1 bg-white/[0.04] border-white/10 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Description courte</Label>
                    <Input
                      value={formData.short_description}
                      onChange={(e) => handleChange('short_description', e.target.value)}
                      placeholder="Description courte (max 200 car.)"
                      maxLength={200}
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Description complète</Label>
                    <Textarea
                      value={formData.description}
                      onChange={(e) => handleChange('description', e.target.value)}
                      placeholder="Description détaillée du produit..."
                      rows={3}
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-white/70 text-xs">Catégorie *</Label>
                      <Select value={formData.category} onValueChange={(v) => handleChange('category', v)}>
                        <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CATEGORIES.map(c => (
                            <SelectItem key={c.value} value={c.value}>{c.icon} {c.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Sous-catégorie</Label>
                      <Input
                        value={formData.subcategory}
                        onChange={(e) => handleChange('subcategory', e.target.value)}
                        placeholder="Ex: Féculents, Froid..."
                        className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-white/70 text-xs">Marque</Label>
                      <Input
                        value={formData.brand}
                        onChange={(e) => handleChange('brand', e.target.value)}
                        className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Fabricant</Label>
                      <Input
                        value={formData.manufacturer}
                        onChange={(e) => handleChange('manufacturer', e.target.value)}
                        className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Tags</Label>
                    <TagInput
                      value={formData.tags}
                      onChange={(v) => handleChange('tags', v)}
                      placeholder="Ajouter un tag..."
                    />
                  </div>
                </div>
              </FormSection>

              <FormSection title="Statut & Options" icon={CheckCircle2}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Statut</Label>
                    <Select value={formData.status} onValueChange={(v) => handleChange('status', v)}>
                      <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="draft">Brouillon</SelectItem>
                        <SelectItem value="pending_approval">En attente</SelectItem>
                        <SelectItem value="approved">Approuvé</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex flex-wrap gap-6 mt-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.is_active} onCheckedChange={(v) => handleChange('is_active', v)} />
                    <span className="text-sm text-white/80">Actif</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.is_new} onCheckedChange={(v) => handleChange('is_new', v)} />
                    <span className="text-sm text-white/80">Nouveauté</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.is_featured} onCheckedChange={(v) => handleChange('is_featured', v)} />
                    <span className="text-sm text-white/80">Mis en avant</span>
                  </label>
                </div>
              </FormSection>
            </TabsContent>
);

export const PricingTab = ({ formData, handleChange }) => (
            <TabsContent value="pricing" className="space-y-4">
              <FormSection title="Tarification" icon={Tag}>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Prix HT (centimes) *</Label>
                    <Input
                      type="number"
                      value={formData.price_ht_cents}
                      onChange={(e) => handleChange('price_ht_cents', e.target.value)}
                      placeholder="1000 = 10,00€"
                      className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                    />
                    <p className="text-xs text-white/40 mt-1">= {formatPrice(formData.price_ht_cents)}</p>
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Taux TVA</Label>
                    <Select value={String(formData.tva_rate)} onValueChange={(v) => handleChange('tva_rate', parseFloat(v))}>
                      <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
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
                    <Label className="text-white/70 text-xs">Unité de vente</Label>
                    <Select value={formData.unit_type} onValueChange={(v) => handleChange('unit_type', v)}>
                      <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {UNITS.map(u => (
                          <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label className="text-white/70 text-xs">Libellé unité</Label>
                  <Input
                    value={formData.unit_label}
                    onChange={(e) => handleChange('unit_label', e.target.value)}
                    placeholder="Ex: sac de 5kg, carton de 12..."
                    className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm"
                  />
                </div>
              </FormSection>

              <FormSection title="Dimensions & Poids" icon={Ruler}>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Longueur (cm)</Label>
                    <Input type="number" value={formData.length_cm} onChange={(e) => handleChange('length_cm', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Largeur (cm)</Label>
                    <Input type="number" value={formData.width_cm} onChange={(e) => handleChange('width_cm', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Hauteur (cm)</Label>
                    <Input type="number" value={formData.height_cm} onChange={(e) => handleChange('height_cm', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Volume (L)</Label>
                    <Input type="number" value={formData.volume_l} onChange={(e) => handleChange('volume_l', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <Label className="text-white/70 text-xs">Poids net (kg)</Label>
                    <Input type="number" step="0.01" value={formData.net_weight_kg} onChange={(e) => handleChange('net_weight_kg', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Poids brut (kg)</Label>
                    <Input type="number" step="0.01" value={formData.gross_weight_kg} onChange={(e) => handleChange('gross_weight_kg', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </div>
              </FormSection>

              <FormSection title="Conditionnement" icon={Box}>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Unités/pack</Label>
                    <Input type="number" value={formData.unit_per_pack} onChange={(e) => handleChange('unit_per_pack', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Packs/carton</Label>
                    <Input type="number" value={formData.pack_per_carton} onChange={(e) => handleChange('pack_per_carton', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Cartons/palette</Label>
                    <Input type="number" value={formData.carton_per_pallet} onChange={(e) => handleChange('carton_per_pallet', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <Label className="text-white/70 text-xs">Type d'emballage</Label>
                    <Input value={formData.packaging_type} onChange={(e) => handleChange('packaging_type', e.target.value)} placeholder="Bouteille, sac, carton..." className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <Checkbox checked={formData.is_recyclable} onCheckedChange={(v) => handleChange('is_recyclable', v)} />
                      <span className="text-sm text-white/80">Emballage recyclable</span>
                    </label>
                  </div>
                </div>
              </FormSection>

              <FormSection title="Origine" icon={Globe}>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Pays d'origine</Label>
                    <Select value={formData.country_code} onValueChange={(v) => handleChange('country_code', v)}>
                      <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                        <SelectValue>
                          {formData.country_code && (
                            <div className="flex items-center gap-2">
                              <CountryFlag countryCode={formData.country_code} size={20} />
                              <span>{COUNTRIES.find(c => c.code === formData.country_code)?.name}</span>
                            </div>
                          )}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRIES.map(c => (
                          <SelectItem key={c.code} value={c.code}>
                            <div className="flex items-center gap-2">
                              <CountryFlag countryCode={c.code} size={20} />
                              <span>{c.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Région</Label>
                    <Input value={formData.region} onChange={(e) => handleChange('region', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Producteur</Label>
                    <Input value={formData.producer_name} onChange={(e) => handleChange('producer_name', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </div>
              </FormSection>
            </TabsContent>
);
