import React, { useState } from 'react';
import {
  Package, Tag, Building2, MapPin, Scale, Ruler, Thermometer,
  Clock, Shield, FileText, Truck, Box, Leaf, Award, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, Download, Info, Zap, Wrench,
  Droplets, Flame, Globe, Calendar, CheckCircle2, XCircle, Star
} from 'lucide-react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import Barcode from 'react-barcode';

// Country flags SVG component
const CountryFlag = ({ countryCode, size = 24 }) => {
  // Map of country codes to their flag SVG paths
  const flags = {
    FR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    ES: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#c60b1e"/>
        <rect y="150" width="900" height="300" fill="#ffc400"/>
      </svg>
    ),
    IT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#009246"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ce2b37"/>
      </svg>
    ),
    DE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#000000"/>
        <rect y="200" width="900" height="200" fill="#DD0000"/>
        <rect y="400" width="900" height="200" fill="#FFCC00"/>
      </svg>
    ),
    BE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#000000"/>
        <rect x="300" width="300" height="600" fill="#FAE042"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    NL: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#AE1C28"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#21468B"/>
      </svg>
    ),
    PT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="360" height="600" fill="#006600"/>
        <rect x="360" width="540" height="600" fill="#FF0000"/>
        <circle cx="360" cy="300" r="100" fill="#FFCC00"/>
      </svg>
    ),
    MA: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#C1272D"/>
        <path d="M450,170 L485,295 L615,295 L510,370 L545,495 L450,420 L355,495 L390,370 L285,295 L415,295 Z" fill="none" stroke="#006233" strokeWidth="15"/>
      </svg>
    ),
    TN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#E70013"/>
        <circle cx="450" cy="300" r="150" fill="#FFFFFF"/>
        <circle cx="480" cy="300" r="120" fill="#E70013"/>
        <path d="M400,300 L450,260 L450,340 Z" fill="#E70013"/>
      </svg>
    ),
    CN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DE2910"/>
        <polygon points="150,100 170,160 230,160 180,200 200,260 150,220 100,260 120,200 70,160 130,160" fill="#FFDE00"/>
      </svg>
    ),
    TH: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="100" fill="#A51931"/>
        <rect y="100" width="900" height="100" fill="#F4F5F8"/>
        <rect y="200" width="900" height="200" fill="#2D2A4A"/>
        <rect y="400" width="900" height="100" fill="#F4F5F8"/>
        <rect y="500" width="900" height="100" fill="#A51931"/>
      </svg>
    ),
    VN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DA251D"/>
        <polygon points="450,120 510,300 690,300 540,400 600,580 450,480 300,580 360,400 210,300 390,300" fill="#FFFF00"/>
      </svg>
    ),
    IN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#FF9933"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#138808"/>
        <circle cx="450" cy="300" r="60" fill="#000080"/>
      </svg>
    ),
    BR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#009B3A"/>
        <polygon points="450,50 850,300 450,550 50,300" fill="#FEDF00"/>
        <circle cx="450" cy="300" r="100" fill="#002776"/>
      </svg>
    ),
    US: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#BF0A30"/>
        <rect y="46" width="900" height="46" fill="#FFFFFF"/>
        <rect y="138" width="900" height="46" fill="#FFFFFF"/>
        <rect y="230" width="900" height="46" fill="#FFFFFF"/>
        <rect y="322" width="900" height="46" fill="#FFFFFF"/>
        <rect y="414" width="900" height="46" fill="#FFFFFF"/>
        <rect y="506" width="900" height="46" fill="#FFFFFF"/>
        <rect width="360" height="322" fill="#002868"/>
      </svg>
    ),
    GB: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#012169"/>
        <path d="M0,0 L900,600 M900,0 L0,600" stroke="#FFFFFF" strokeWidth="100"/>
        <path d="M0,0 L900,600 M900,0 L0,600" stroke="#C8102E" strokeWidth="60"/>
        <path d="M450,0 V600 M0,300 H900" stroke="#FFFFFF" strokeWidth="150"/>
        <path d="M450,0 V600 M0,300 H900" stroke="#C8102E" strokeWidth="90"/>
      </svg>
    ),
    GP: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    MQ: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    GF: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    RE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
  };
  
  return flags[countryCode] || (
    <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
      <rect width="900" height="600" fill="#cccccc"/>
      <text x="450" y="320" textAnchor="middle" fontSize="200" fill="#666666">{countryCode}</text>
    </svg>
  );
};

// Format currency
const formatCurrency = (cents, currency = 'EUR') => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: currency
  }).format(cents / 100);
};

// Get category label
const getCategoryLabel = (category) => {
  const labels = {
    alimentaire: 'Alimentaire',
    boissons: 'Boissons',
    materiaux: 'Matériaux',
    equipements: 'Équipements',
    matieres_premieres: 'Matières premières',
    hygiene: 'Hygiène',
    chimie: 'Chimie',
    textile: 'Textile',
    electronique: 'Électronique',
    autre: 'Autre'
  };
  return labels[category] || category;
};

// Get status badge
const getStatusBadge = (status) => {
  const config = {
    draft: { label: 'Brouillon', class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
    pending_approval: { label: 'En attente', class: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
    approved: { label: 'Approuvé', class: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
    rejected: { label: 'Rejeté', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
    discontinued: { label: 'Arrêté', class: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    out_of_stock: { label: 'Rupture', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' }
  };
  return config[status] || config.draft;
};

// Get temperature label
const getTemperatureLabel = (range) => {
  const labels = {
    ambient: 'Température ambiante (15-25°C)',
    refrigerated: 'Réfrigéré (0-4°C)',
    frozen: 'Surgelé (-18°C)',
    deep_frozen: 'Surgélation profonde (-25°C)',
    controlled: 'Température contrôlée'
  };
  return labels[range] || range;
};

// Section component
const Section = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-white/[0.08] rounded-xl overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="w-5 h-5 text-[#D9B35A]" />}
          <span className="font-semibold text-white">{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>
      {isOpen && (
        <div className="p-4 border-t border-white/[0.08]">
          {children}
        </div>
      )}
    </div>
  );
};

// Data row component
const DataRow = ({ label, value, icon: Icon, highlight = false }) => {
  if (!value && value !== 0) return null;
  
  return (
    <div className={`flex justify-between items-center py-2 ${highlight ? 'bg-[#D9B35A]/10 -mx-2 px-2 rounded-lg' : ''}`}>
      <span className="text-white/60 flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4" />}
        {label}
      </span>
      <span className={`font-medium ${highlight ? 'text-[#D9B35A]' : 'text-white/90'}`}>{value}</span>
    </div>
  );
};

// Main component
export default function ProductCardView({ product, showActions = true }) {
  const [activeTab, setActiveTab] = useState('general');
  
  if (!product) return null;
  
  const statusConfig = getStatusBadge(product.status);
  const isFood = ['alimentaire', 'boissons'].includes(product.category);
  const isEquipment = ['equipements', 'electronique'].includes(product.category);
  const isMaterial = ['materiaux', 'matieres_premieres', 'chimie'].includes(product.category);
  
  // Calculate TTC price
  const priceTTC = product.pricing?.price_ht_cents 
    ? Math.round(product.pricing.price_ht_cents * (1 + (product.pricing.tva_rate || 20) / 100))
    : null;

  return (
    <div className="space-y-6" data-testid="product-card-view">
      {/* Header */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Image */}
        <div className="lg:w-1/3">
          <div className="aspect-square rounded-2xl bg-white/[0.04] border border-white/[0.08] overflow-hidden flex items-center justify-center">
            {product.media?.main_image_url ? (
              <img 
                src={product.media.main_image_url} 
                alt={product.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Package className="w-20 h-20 text-white/20" />
            )}
          </div>
          
          {/* Badges */}
          <div className="flex flex-wrap gap-2 mt-4">
            <Badge variant="outline" className={statusConfig.class}>
              {statusConfig.label}
            </Badge>
            {product.is_new && (
              <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Nouveau</Badge>
            )}
            {product.is_featured && (
              <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                <Star className="w-3 h-3 mr-1" /> Mis en avant
              </Badge>
            )}
            {product.compliance?.organic_certified && (
              <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                <Leaf className="w-3 h-3 mr-1" /> Bio
              </Badge>
            )}
          </div>
        </div>
        
        {/* Info principale */}
        <div className="lg:w-2/3 space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="bg-white/[0.04] border-white/10">
                {getCategoryLabel(product.category)}
              </Badge>
              {product.subcategory && (
                <Badge variant="outline" className="bg-white/[0.04] border-white/10">
                  {product.subcategory}
                </Badge>
              )}
            </div>
            
            <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">{product.name}</h1>
            
            {product.brand && (
              <p className="text-[#D9B35A] font-medium">{product.brand}</p>
            )}
            
            {product.short_description && (
              <p className="text-white/60 mt-2">{product.short_description}</p>
            )}
          </div>
          
          {/* Codes */}
          <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-white/40" />
              <span className="text-white/60">SKU:</span>
              <span className="font-mono text-white">{product.sku}</span>
            </div>
            {product.ean && (
              <div className="flex items-center gap-2">
                <Barcode className="w-4 h-4 text-white/40" />
                <span className="text-white/60">EAN:</span>
                <span className="font-mono text-white">{product.ean}</span>
              </div>
            )}
            {product.manufacturer_ref && (
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-white/40" />
                <span className="text-white/60">Réf. fab.:</span>
                <span className="font-mono text-white">{product.manufacturer_ref}</span>
              </div>
            )}
          </div>
          
          {/* Prix */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-[#D9B35A]/10 to-[#D9B35A]/5 border border-[#D9B35A]/20">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-white/60 text-sm">Prix unitaire HT</p>
                <p className="text-3xl font-bold text-[#D9B35A]">
                  {formatCurrency(product.pricing?.price_ht_cents, product.pricing?.currency)}
                </p>
                <p className="text-white/50 text-sm">
                  TVA {product.pricing?.tva_rate || 20}% · TTC: {formatCurrency(priceTTC, product.pricing?.currency)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-white/60 text-sm">Unité de vente</p>
                <p className="text-lg font-semibold text-white">{product.unit_label || product.unit_type}</p>
              </div>
            </div>
            
            {/* Tarifs dégressifs */}
            {product.pricing?.tier_pricing && product.pricing.tier_pricing.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[#D9B35A]/20">
                <p className="text-sm text-white/60 mb-2">Tarifs dégressifs</p>
                <div className="flex flex-wrap gap-2">
                  {product.pricing.tier_pricing.map((tier) => (
                    <Badge key={`tier-${tier.min_qty}-${tier.price_ht_cents}`} variant="outline" className="bg-white/[0.04] border-white/10">
                      ≥{tier.min_qty}: {formatCurrency(tier.price_ht_cents)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Code-barres EAN-13 scannable */}
          {product.ean && (
            <div className="p-4 bg-white rounded-xl">
              <div className="flex flex-col items-center">
                <p className="text-xs text-gray-500 mb-2 font-medium">Code EAN-13</p>
                <Barcode 
                  value={product.ean} 
                  format="EAN13" 
                  width={2.5} 
                  height={70} 
                  fontSize={14}
                  textAlign="center"
                  textPosition="bottom"
                  textMargin={6}
                  background="#ffffff"
                  lineColor="#000000"
                  margin={10}
                  displayValue={true}
                />
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Tabs détaillés */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl flex-wrap h-auto">
          <TabsTrigger value="general" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
            <Info className="w-4 h-4 mr-2" />
            Général
          </TabsTrigger>
          {isFood && (
            <TabsTrigger value="nutrition" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
              <Droplets className="w-4 h-4 mr-2" />
              Nutrition
            </TabsTrigger>
          )}
          {(isEquipment || isMaterial) && (
            <TabsTrigger value="technical" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
              <Wrench className="w-4 h-4 mr-2" />
              Technique
            </TabsTrigger>
          )}
          <TabsTrigger value="logistics" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
            <Truck className="w-4 h-4 mr-2" />
            Logistique
          </TabsTrigger>
          <TabsTrigger value="compliance" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
            <Shield className="w-4 h-4 mr-2" />
            Conformité
          </TabsTrigger>
          <TabsTrigger value="documents" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg">
            <FileText className="w-4 h-4 mr-2" />
            Documents
          </TabsTrigger>
        </TabsList>
        
        {/* TAB: Général */}
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
        
        {/* TAB: Nutrition */}
        {isFood && (
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
        )}
        
        {/* TAB: Technique */}
        {(isEquipment || isMaterial) && (
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
        )}
        
        {/* TAB: Logistique */}
        <TabsContent value="logistics" className="space-y-4 mt-4">
          {/* Stock */}
          {product.stock && (
            <Section title="Stock" icon={Box}>
              <div className="grid sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <p className="text-3xl font-bold text-emerald-400">{product.stock.quantity_available}</p>
                  <p className="text-sm text-white/60">Disponible</p>
                </div>
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
                  <p className="text-3xl font-bold text-amber-400">{product.stock.quantity_reserved}</p>
                  <p className="text-sm text-white/60">Réservé</p>
                </div>
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-center">
                  <p className="text-3xl font-bold text-blue-400">{product.stock.quantity_incoming}</p>
                  <p className="text-sm text-white/60">En commande</p>
                </div>
              </div>
            </Section>
          )}
          
          {/* Logistique */}
          {product.logistics && (
            <Section title="Transport & Livraison" icon={Truck}>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <DataRow label="Délai standard" value={`${product.logistics.lead_time_days} jours`} icon={Clock} />
                  <DataRow label="Qté min commande" value={product.logistics.min_order_quantity} />
                  <DataRow label="Multiple commande" value={product.logistics.order_multiple} />
                  <DataRow label="Code douanier" value={product.logistics.customs_code} />
                </div>
                <div className="space-y-2">
                  {product.logistics.is_fragile && (
                    <div className="flex items-center gap-2 text-amber-400">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Produit fragile</span>
                    </div>
                  )}
                  {product.logistics.requires_adr && (
                    <div className="flex items-center gap-2 text-red-400">
                      <Flame className="w-4 h-4" />
                      <span>Transport ADR requis</span>
                    </div>
                  )}
                  {product.logistics.is_stackable && (
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Gerbage autorisé</span>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Zones */}
              {product.logistics.available_zones?.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-white/70 mb-2">Zones de disponibilité</p>
                  <div className="flex flex-wrap gap-2">
                    {product.logistics.available_zones.map((z) => (
                      <Badge key={`zone-${z}`} className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">{z}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          )}
        </TabsContent>
        
        {/* TAB: Conformité */}
        <TabsContent value="compliance" className="space-y-4 mt-4">
          {product.compliance && (
            <Section title="Conformité & Certifications" icon={Shield}>
              <div className="grid sm:grid-cols-2 gap-6">
                {/* Marquages */}
                <div>
                  <p className="text-sm font-medium text-white/70 mb-3">Marquages</p>
                  <div className="space-y-2">
                    <div className={`flex items-center gap-2 ${product.compliance.ce_marking ? 'text-emerald-400' : 'text-white/30'}`}>
                      {product.compliance.ce_marking ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      <span>Marquage CE</span>
                    </div>
                    <div className={`flex items-center gap-2 ${product.compliance.nf_marking ? 'text-emerald-400' : 'text-white/30'}`}>
                      {product.compliance.nf_marking ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      <span>Marque NF</span>
                    </div>
                  </div>
                </div>
                
                {/* Certifications */}
                <div>
                  <p className="text-sm font-medium text-white/70 mb-3">Certifications</p>
                  <div className="space-y-2">
                    {product.compliance.organic_certified && (
                      <div className="flex items-center gap-2 text-green-400">
                        <Leaf className="w-4 h-4" />
                        <span>Bio {product.compliance.organic_label && `(${product.compliance.organic_label})`}</span>
                      </div>
                    )}
                    {product.compliance.haccp_compliant && (
                      <div className="flex items-center gap-2 text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>HACCP</span>
                      </div>
                    )}
                    {product.compliance.reach_compliant && (
                      <div className="flex items-center gap-2 text-blue-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>REACH</span>
                      </div>
                    )}
                    {product.compliance.rohs_compliant && (
                      <div className="flex items-center gap-2 text-purple-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>RoHS</span>
                      </div>
                    )}
                    {product.compliance.fsc_certified && (
                      <div className="flex items-center gap-2 text-green-400">
                        <Leaf className="w-4 h-4" />
                        <span>FSC</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Classe de danger */}
              {product.compliance.hazard_class && product.compliance.hazard_class !== 'none' && (
                <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                  <div className="flex items-center gap-2 text-red-400">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-semibold">Classe de danger: {product.compliance.hazard_class}</span>
                  </div>
                </div>
              )}
            </Section>
          )}
        </TabsContent>
        
        {/* TAB: Documents */}
        <TabsContent value="documents" className="space-y-4 mt-4">
          <Section title="Documents" icon={FileText}>
            <div className="grid sm:grid-cols-2 gap-4">
              {product.media?.technical_sheet_url && (
                <a 
                  href={product.media.technical_sheet_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-blue-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Fiche technique</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {product.media?.user_manual_url && (
                <a 
                  href={product.media.user_manual_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-purple-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Manuel utilisateur</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {product.compliance?.safety_data_sheet_url && (
                <a 
                  href={product.compliance.safety_data_sheet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-amber-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Fiche de données sécurité</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {(!product.media?.technical_sheet_url && !product.media?.user_manual_url && !product.compliance?.safety_data_sheet_url) && (
                <div className="col-span-2 text-center py-8 text-white/50">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Aucun document disponible</p>
                </div>
              )}
            </div>
          </Section>
        </TabsContent>
      </Tabs>
      
      {/* Vendor info */}
      {product.vendor_name && (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-[#D9B35A]" />
            <div>
              <p className="text-sm text-white/60">Vendeur</p>
              <p className="font-medium text-white">{product.vendor_name}</p>
            </div>
          </div>
          {product.vendor_id && (
            <Badge variant="outline" className="bg-white/[0.04] border-white/10 font-mono text-xs">
              {product.vendor_id}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
