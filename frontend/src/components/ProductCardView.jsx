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
import {
  CountryFlag, formatCurrency, getCategoryLabel, getStatusBadge,
  getTemperatureLabel, Section, DataRow,
} from './product-card/productCardUtils';
import { GeneralTab, NutritionTab, TechnicalTab } from './product-card/ProductCardTabsGeneral';
import { LogisticsTab, ComplianceTab, DocumentsTab } from './product-card/ProductCardTabsLogistics';

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
        <GeneralTab product={product} />
        {isFood && <NutritionTab product={product} />}
        {(isEquipment || isMaterial) && <TechnicalTab product={product} />}
        <LogisticsTab product={product} />
        <ComplianceTab product={product} />
        <DocumentsTab product={product} />
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
