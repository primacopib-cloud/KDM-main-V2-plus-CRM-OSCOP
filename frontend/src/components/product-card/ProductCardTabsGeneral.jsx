import React from 'react';
import {
  Package, Tag, Building2, MapPin, Scale, Ruler, Thermometer,
  Clock, Shield, FileText, Truck, Box, Leaf, Award, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, Download, Info, Zap, Wrench,
  Droplets, Flame, Globe, Calendar, CheckCircle2, XCircle, Star
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import Barcode from 'react-barcode';
import {
  CountryFlag, formatCurrency, getCategoryLabel, getStatusBadge,
  getTemperatureLabel, Section, DataRow,
} from './productCardUtils';

export const GeneralTab = ({ product }) => (
        <TabsContent value="general" className="space-y-4 mt-4">
          {product.description && (
            <Section title="Description" icon={Info}>
              <p className="text-white/80 whitespace-pre-wrap">{product.description}</p>
            </Section>
          )}
          
          {/* Dimensions & Poids */}
          {(product.dimensions || product.weight) && (
            <Section title="Dimensions & Poids" icon={Ruler}>
              <div className="grid sm:grid-cols-2 gap-4">
                {product.dimensions && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-white/70">Dimensions</p>
                    <DataRow label="Longueur" value={product.dimensions.length_cm ? `${product.dimensions.length_cm} cm` : null} />
                    <DataRow label="Largeur" value={product.dimensions.width_cm ? `${product.dimensions.width_cm} cm` : null} />
                    <DataRow label="Hauteur" value={product.dimensions.height_cm ? `${product.dimensions.height_cm} cm` : null} />
                    <DataRow label="Diamètre" value={product.dimensions.diameter_cm ? `${product.dimensions.diameter_cm} cm` : null} />
                    <DataRow label="Volume" value={product.dimensions.volume_l ? `${product.dimensions.volume_l} L` : null} />
                  </div>
                )}
                {product.weight && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-white/70">Poids</p>
                    <DataRow label="Poids net" value={product.weight.net_weight_kg ? `${product.weight.net_weight_kg} kg` : null} />
                    <DataRow label="Poids brut" value={product.weight.gross_weight_kg ? `${product.weight.gross_weight_kg} kg` : null} />
                    <DataRow label="Poids égoutté" value={product.weight.drained_weight_kg ? `${product.weight.drained_weight_kg} kg` : null} />
                  </div>
                )}
              </div>
            </Section>
          )}
          
          {/* Origine */}
          {product.origin && (
            <Section title="Origine & Traçabilité" icon={Globe}>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  {/* Pays avec drapeau */}
                  {product.origin.country_code && (
                    <div className="flex justify-between items-center py-2">
                      <span className="text-white/60 flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        Pays
                      </span>
                      <div className="flex items-center gap-2">
                        <CountryFlag countryCode={product.origin.country_code} size={28} />
                        <span className="font-medium text-white/90">{product.origin.country_name}</span>
                      </div>
                    </div>
                  )}
                  <DataRow label="Région" value={product.origin.region} />
                  <DataRow label="Producteur" value={product.origin.producer_name} icon={Building2} />
                </div>
                <div className="space-y-2">
                  {product.origin.aoc_aop && <DataRow label="AOC/AOP" value={product.origin.aoc_aop} highlight />}
                  {product.origin.igp && <DataRow label="IGP" value={product.origin.igp} highlight />}
                  {product.origin.label_rouge && <DataRow label="Label Rouge" value="Oui" highlight />}
                </div>
              </div>
            </Section>
          )}
          
          {/* Conditionnement */}
          {product.packaging && (
            <Section title="Conditionnement" icon={Box}>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <DataRow label="Unités/pack" value={product.packaging.unit_per_pack} />
                  <DataRow label="Packs/carton" value={product.packaging.pack_per_carton} />
                  <DataRow label="Cartons/palette" value={product.packaging.carton_per_pallet} />
                  <DataRow label="Unités/palette" value={product.packaging.units_per_pallet} />
                </div>
                <div className="space-y-2">
                  <DataRow label="Type emballage" value={product.packaging.packaging_type} />
                  <DataRow label="Matériau" value={product.packaging.packaging_material} />
                  {product.packaging.is_recyclable && (
                    <div className="flex items-center gap-2 text-emerald-400">
                      <Leaf className="w-4 h-4" />
                      <span>Emballage recyclable</span>
                    </div>
                  )}
                </div>
              </div>
            </Section>
          )}
          
          {/* Conservation */}
          {product.conservation && (
            <Section title="Conservation" icon={Thermometer}>
              <div className="space-y-2">
                <DataRow 
                  label="Température" 
                  value={getTemperatureLabel(product.conservation.temperature_range)} 
                  icon={Thermometer}
                  highlight
                />
                {product.conservation.temperature_min_c !== null && (
                  <DataRow label="Plage" value={`${product.conservation.temperature_min_c}°C à ${product.conservation.temperature_max_c}°C`} />
                )}
                <DataRow label="DLC/DDM" value={product.conservation.dlc_type} />
                <DataRow label="Durée conservation" value={product.conservation.shelf_life_days ? `${product.conservation.shelf_life_days} jours` : null} icon={Clock} />
                <DataRow label="Après ouverture" value={product.conservation.opened_shelf_life_days ? `${product.conservation.opened_shelf_life_days} jours` : null} />
                {product.conservation.storage_instructions && (
                  <div className="mt-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
                    <p className="text-sm text-white/60">Instructions de stockage</p>
                    <p className="text-white/80 mt-1">{product.conservation.storage_instructions}</p>
                  </div>
                )}
              </div>
            </Section>
          )}
        </TabsContent>
);

export const NutritionTab = ({ product }) => (
          <TabsContent value="nutrition" className="space-y-4 mt-4">
            {/* Ingrédients */}
            {product.ingredients && (
              <Section title="Ingrédients" icon={Info}>
                <p className="text-white/80">{product.ingredients}</p>
              </Section>
            )}
            
            {/* Valeurs nutritionnelles */}
            {product.nutrition && (
              <Section title="Valeurs nutritionnelles" icon={Droplets}>
                <div className="grid sm:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <p className="text-sm text-white/50 mb-3">Pour 100g</p>
                    <DataRow label="Énergie" value={product.nutrition.energy_kcal ? `${product.nutrition.energy_kcal} kcal` : null} highlight />
                    <DataRow label="Matières grasses" value={product.nutrition.fat_g ? `${product.nutrition.fat_g} g` : null} />
                    <DataRow label="dont saturés" value={product.nutrition.saturated_fat_g ? `${product.nutrition.saturated_fat_g} g` : null} />
                    <DataRow label="Glucides" value={product.nutrition.carbohydrates_g ? `${product.nutrition.carbohydrates_g} g` : null} />
                    <DataRow label="dont sucres" value={product.nutrition.sugars_g ? `${product.nutrition.sugars_g} g` : null} />
                    <DataRow label="Fibres" value={product.nutrition.fiber_g ? `${product.nutrition.fiber_g} g` : null} />
                    <DataRow label="Protéines" value={product.nutrition.protein_g ? `${product.nutrition.protein_g} g` : null} />
                    <DataRow label="Sel" value={product.nutrition.salt_g ? `${product.nutrition.salt_g} g` : null} />
                  </div>
                  
                  {/* Nutri-Score */}
                  {product.nutrition.nutri_score && (
                    <div className="flex items-center justify-center">
                      <div className={`w-20 h-20 rounded-2xl flex items-center justify-center text-4xl font-bold ${
                        product.nutrition.nutri_score === 'A' ? 'bg-green-500 text-white' :
                        product.nutrition.nutri_score === 'B' ? 'bg-lime-500 text-white' :
                        product.nutrition.nutri_score === 'C' ? 'bg-yellow-500 text-black' :
                        product.nutrition.nutri_score === 'D' ? 'bg-orange-500 text-white' :
                        'bg-red-500 text-white'
                      }`}>
                        {product.nutrition.nutri_score}
                      </div>
                    </div>
                  )}
                </div>
              </Section>
            )}
            
            {/* Allergènes */}
            {product.allergens && (
              <Section title="Allergènes" icon={AlertTriangle}>
                <div className="space-y-4">
                  {product.allergens.contains?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-red-400 mb-2">Contient</p>
                      <div className="flex flex-wrap gap-2">
                        {product.allergens.contains.map((a, i) => (
                          <Badge key={i} className="bg-red-500/20 text-red-400 border-red-500/30">{a}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {product.allergens.may_contain?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-amber-400 mb-2">Peut contenir (traces)</p>
                      <div className="flex flex-wrap gap-2">
                        {product.allergens.may_contain.map((a) => (
                          <Badge key={`may-${a}`} className="bg-amber-500/20 text-amber-400 border-amber-500/30">{a}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {product.allergens.free_from?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-emerald-400 mb-2">Sans (garanti)</p>
                      <div className="flex flex-wrap gap-2">
                        {product.allergens.free_from.map((a) => (
                          <Badge key={`free-${a}`} className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">{a}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Section>
            )}
          </TabsContent>
);

export const TechnicalTab = ({ product }) => (
          <TabsContent value="technical" className="space-y-4 mt-4">
            {product.technical_specs && (
              <Section title="Spécifications techniques" icon={Wrench}>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <DataRow label="Matériau" value={product.technical_specs.material} />
                    <DataRow label="Composition" value={product.technical_specs.composition} />
                    <DataRow label="Couleur" value={product.technical_specs.color} />
                    <DataRow label="Finition" value={product.technical_specs.finish} />
                    <DataRow label="Capacité" value={product.technical_specs.capacity} />
                  </div>
                  <div className="space-y-2">
                    <DataRow label="Puissance" value={product.technical_specs.power_watts ? `${product.technical_specs.power_watts} W` : null} icon={Zap} />
                    <DataRow label="Tension" value={product.technical_specs.voltage} />
                    <DataRow label="Charge max" value={product.technical_specs.load_capacity_kg ? `${product.technical_specs.load_capacity_kg} kg` : null} />
                    <DataRow label="Pression" value={product.technical_specs.pressure_bar ? `${product.technical_specs.pressure_bar} bar` : null} />
                    <DataRow label="Résistance temp." value={product.technical_specs.temperature_resistance_c ? `${product.technical_specs.temperature_resistance_c}°C` : null} />
                  </div>
                </div>
                
                {/* Normes */}
                {product.technical_specs.norms?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-white/70 mb-2">Normes</p>
                    <div className="flex flex-wrap gap-2">
                      {product.technical_specs.norms.map((n) => (
                        <Badge key={`norm-${n}`} variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">{n}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Spécifications personnalisées */}
                {product.technical_specs.custom_specs && Object.keys(product.technical_specs.custom_specs).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-white/[0.08]">
                    <p className="text-sm font-medium text-white/70 mb-2">Caractéristiques</p>
                    <div className="space-y-2">
                      {Object.entries(product.technical_specs.custom_specs).map(([key, value]) => (
                        <DataRow key={key} label={key} value={value} />
                      ))}
                    </div>
                  </div>
                )}
              </Section>
            )}
            
            {/* Garantie */}
            {product.warranty && (
              <Section title="Garantie" icon={Shield}>
                <div className="space-y-2">
                  <DataRow label="Durée" value={`${product.warranty.duration_months} mois`} highlight />
                  <DataRow label="Type" value={product.warranty.warranty_type} />
                  {product.warranty.coverage && <DataRow label="Couverture" value={product.warranty.coverage} />}
                  {product.warranty.manufacturer_warranty && (
                    <div className="flex items-center gap-2 text-emerald-400 mt-2">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Garantie fabricant</span>
                    </div>
                  )}
                </div>
              </Section>
            )}
          </TabsContent>
);

