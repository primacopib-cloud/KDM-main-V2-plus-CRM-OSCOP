import {
  Thermometer, Leaf, Droplets, AlertTriangle, Wrench, Shield, Truck, MapPin,
} from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { TabsContent } from '../ui/tabs';
import { FormSection, TagInput } from './FormInputs';
import { TEMP_RANGES, ALLERGENS, ZONES } from './constants';

export const FoodTab = ({ formData, handleChange }) => (
              <TabsContent value="food" className="space-y-4">
                <FormSection title="Conservation" icon={Thermometer}>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label className="text-white/70 text-xs">Température</Label>
                      <Select value={formData.temperature_range} onValueChange={(v) => handleChange('temperature_range', v)}>
                        <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {TEMP_RANGES.map(t => (
                            <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Durée (jours)</Label>
                      <Input type="number" value={formData.shelf_life_days} onChange={(e) => handleChange('shelf_life_days', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Type date</Label>
                      <Select value={formData.dlc_type} onValueChange={(v) => handleChange('dlc_type', v)}>
                        <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="DLC">DLC (Date limite)</SelectItem>
                          <SelectItem value="DDM">DDM (Date durabilité)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Instructions de stockage</Label>
                    <Textarea value={formData.storage_instructions} onChange={(e) => handleChange('storage_instructions', e.target.value)} rows={2} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </FormSection>

                <FormSection title="Ingrédients" icon={Leaf}>
                  <div>
                    <Label className="text-white/70 text-xs">Liste des ingrédients</Label>
                    <Textarea value={formData.ingredients} onChange={(e) => handleChange('ingredients', e.target.value)} rows={3} placeholder="Ex: Farine de blé, eau, sel..." className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </FormSection>

                <FormSection title="Valeurs nutritionnelles" icon={Droplets} defaultOpen={false}>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label className="text-white/70 text-xs">Énergie (kcal/100g)</Label>
                      <Input type="number" value={formData.energy_kcal} onChange={(e) => handleChange('energy_kcal', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Matières grasses (g)</Label>
                      <Input type="number" step="0.1" value={formData.fat_g} onChange={(e) => handleChange('fat_g', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Glucides (g)</Label>
                      <Input type="number" step="0.1" value={formData.carbohydrates_g} onChange={(e) => handleChange('carbohydrates_g', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Protéines (g)</Label>
                      <Input type="number" step="0.1" value={formData.protein_g} onChange={(e) => handleChange('protein_g', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Sel (g)</Label>
                      <Input type="number" step="0.01" value={formData.salt_g} onChange={(e) => handleChange('salt_g', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Nutri-Score</Label>
                      <Select value={formData.nutri_score} onValueChange={(v) => handleChange('nutri_score', v)}>
                        <SelectTrigger className="mt-1 bg-white/[0.04] border-white/10">
                          <SelectValue placeholder="Sélectionner" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="A">A</SelectItem>
                          <SelectItem value="B">B</SelectItem>
                          <SelectItem value="C">C</SelectItem>
                          <SelectItem value="D">D</SelectItem>
                          <SelectItem value="E">E</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </FormSection>

                <FormSection title="Allergènes" icon={AlertTriangle} defaultOpen={false}>
                  <div className="space-y-4">
                    <div>
                      <Label className="text-white/70 text-xs mb-2 block">Contient</Label>
                      <div className="flex flex-wrap gap-2">
                        {ALLERGENS.map(a => (
                          <label key={a} className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox
                              checked={formData.allergens_contains?.includes(a)}
                              onCheckedChange={(v) => {
                                const current = formData.allergens_contains || [];
                                handleChange('allergens_contains', v ? [...current, a] : current.filter(x => x !== a));
                              }}
                            />
                            <span className="text-xs text-white/70 capitalize">{a}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs mb-2 block">Peut contenir (traces)</Label>
                      <div className="flex flex-wrap gap-2">
                        {ALLERGENS.map(a => (
                          <label key={a} className="flex items-center gap-1.5 cursor-pointer">
                            <Checkbox
                              checked={formData.allergens_may_contain?.includes(a)}
                              onCheckedChange={(v) => {
                                const current = formData.allergens_may_contain || [];
                                handleChange('allergens_may_contain', v ? [...current, a] : current.filter(x => x !== a));
                              }}
                            />
                            <span className="text-xs text-white/70 capitalize">{a}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </FormSection>
              </TabsContent>
);

export const TechnicalTab = ({ formData, handleChange }) => (
              <TabsContent value="technical" className="space-y-4">
                <FormSection title="Spécifications techniques" icon={Wrench}>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label className="text-white/70 text-xs">Matériau</Label>
                      <Input value={formData.material} onChange={(e) => handleChange('material', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Puissance (W)</Label>
                      <Input type="number" value={formData.power_watts} onChange={(e) => handleChange('power_watts', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                    <div>
                      <Label className="text-white/70 text-xs">Tension</Label>
                      <Input value={formData.voltage} onChange={(e) => handleChange('voltage', e.target.value)} placeholder="220-240V" className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                    </div>
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Normes</Label>
                    <TagInput value={formData.norms} onChange={(v) => handleChange('norms', v)} placeholder="CE, NF, ISO..." />
                  </div>
                </FormSection>

                <FormSection title="Garantie" icon={Shield}>
                  <div>
                    <Label className="text-white/70 text-xs">Durée garantie (mois)</Label>
                    <Input type="number" value={formData.warranty_months} onChange={(e) => handleChange('warranty_months', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm w-32" />
                  </div>
                </FormSection>
              </TabsContent>
);

export const LogisticsTab = ({ formData, handleChange }) => (
            <TabsContent value="logistics" className="space-y-4">
              <FormSection title="Livraison" icon={Truck}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-white/70 text-xs">Délai standard (jours)</Label>
                    <Input type="number" value={formData.lead_time_days} onChange={(e) => handleChange('lead_time_days', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                  <div>
                    <Label className="text-white/70 text-xs">Qté min commande</Label>
                    <Input type="number" value={formData.min_order_quantity} onChange={(e) => handleChange('min_order_quantity', e.target.value)} className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm" />
                  </div>
                </div>
                <div className="flex gap-6 mt-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.is_fragile} onCheckedChange={(v) => handleChange('is_fragile', v)} />
                    <span className="text-sm text-white/80">Produit fragile</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.requires_adr} onCheckedChange={(v) => handleChange('requires_adr', v)} />
                    <span className="text-sm text-white/80">Transport ADR</span>
                  </label>
                </div>
              </FormSection>

              <FormSection title="Zones de disponibilité" icon={MapPin}>
                <div className="flex flex-wrap gap-3">
                  {ZONES.map(z => (
                    <label key={z.code} className="flex items-center gap-2 cursor-pointer">
                      <Checkbox
                        checked={formData.available_zones?.includes(z.code)}
                        onCheckedChange={(v) => {
                          const current = formData.available_zones || [];
                          handleChange('available_zones', v ? [...current, z.code] : current.filter(x => x !== z.code));
                        }}
                      />
                      <span className="text-sm text-white/80">{z.name}</span>
                    </label>
                  ))}
                </div>
              </FormSection>

              <FormSection title="Conformité" icon={Shield}>
                <div className="flex flex-wrap gap-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.ce_marking} onCheckedChange={(v) => handleChange('ce_marking', v)} />
                    <span className="text-sm text-white/80">Marquage CE</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.haccp_compliant} onCheckedChange={(v) => handleChange('haccp_compliant', v)} />
                    <span className="text-sm text-white/80">HACCP</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.organic_certified} onCheckedChange={(v) => handleChange('organic_certified', v)} />
                    <span className="text-sm text-white/80">Bio</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox checked={formData.reach_compliant} onCheckedChange={(v) => handleChange('reach_compliant', v)} />
                    <span className="text-sm text-white/80">REACH</span>
                  </label>
                </div>
              </FormSection>
            </TabsContent>
);
