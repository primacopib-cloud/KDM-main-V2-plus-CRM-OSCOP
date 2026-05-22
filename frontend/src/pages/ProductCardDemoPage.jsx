import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Package, Utensils, Wrench, Factory, Droplets } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import ProductCardView from '../components/ProductCardView';

// Exemples de produits par catégorie
const DEMO_PRODUCTS = {
  alimentaire: {
    id: "prod_alim_001",
    sku: "KDM-RIZ-5KG",
    ean: "3760012345670",
    manufacturer_ref: "RIZ-LONG-5",
    name: "Riz Long Grain Premium",
    short_description: "Riz long grain de qualité supérieure, idéal pour la restauration",
    description: "Riz long grain étuvé de qualité premium. Grain ferme et non collant après cuisson. Idéal pour accompagnements, salades et plats exotiques. Conditionné en sac de 5kg pour la restauration professionnelle.",
    category: "alimentaire",
    subcategory: "Féculents",
    tags: ["riz", "féculent", "restauration", "vrac"],
    brand: "KDMARCHE Selection",
    manufacturer: "Rizières de Camargue",
    status: "approved",
    is_active: true,
    is_new: false,
    is_featured: true,
    unit_type: "kg",
    unit_label: "sac de 5kg",
    dimensions: {
      length_cm: 40,
      width_cm: 25,
      height_cm: 8
    },
    weight: {
      net_weight_kg: 5,
      gross_weight_kg: 5.2
    },
    pricing: {
      price_ht_cents: 1250,
      currency: "EUR",
      tva_rate: 5.5,
      tier_pricing: [
        { min_qty: 10, price_ht_cents: 1150 },
        { min_qty: 50, price_ht_cents: 1050 },
        { min_qty: 100, price_ht_cents: 950 }
      ]
    },
    stock: {
      quantity_available: 450,
      quantity_reserved: 25,
      quantity_incoming: 200,
      reorder_threshold: 100
    },
    packaging: {
      unit_per_pack: 1,
      pack_per_carton: 4,
      carton_per_pallet: 60,
      units_per_pallet: 240,
      packaging_type: "sac",
      packaging_material: "plastique recyclable",
      is_recyclable: true
    },
    origin: {
      country_code: "FR",
      country_name: "France",
      region: "Camargue",
      producer_name: "Rizières de Camargue SARL",
      igp: "Riz de Camargue"
    },
    nutrition: {
      serving_size_g: 100,
      energy_kcal: 350,
      energy_kj: 1470,
      fat_g: 0.8,
      saturated_fat_g: 0.2,
      carbohydrates_g: 78,
      sugars_g: 0.1,
      fiber_g: 1.4,
      protein_g: 7.5,
      salt_g: 0.01,
      nutri_score: "A"
    },
    allergens: {
      contains: [],
      may_contain: ["gluten"],
      free_from: ["oeufs", "lait", "arachides", "soja"]
    },
    conservation: {
      temperature_range: "ambient",
      temperature_min_c: 15,
      temperature_max_c: 25,
      shelf_life_days: 730,
      dlc_type: "DDM",
      storage_instructions: "Conserver dans un endroit frais et sec, à l'abri de la lumière"
    },
    ingredients: "Riz long grain (100%)",
    compliance: {
      haccp_compliant: true,
      organic_certified: false
    },
    logistics: {
      customs_code: "1006309800",
      is_stackable: true,
      is_fragile: false,
      lead_time_days: 2,
      min_order_quantity: 4,
      order_multiple: 4,
      available_zones: ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "MAYOTTE"]
    },
    vendor_id: "vendor_001",
    vendor_name: "KDMARCHE Distribution"
  },
  
  equipements: {
    id: "prod_equip_001",
    sku: "KDM-FRIGO-400L",
    ean: "3760098765430",
    manufacturer_ref: "RF-400-PRO",
    name: "Réfrigérateur Professionnel 400L",
    short_description: "Réfrigérateur positif professionnel, idéal pour la restauration",
    description: "Réfrigérateur professionnel 400 litres avec porte vitrée. Température réglable de 0 à +10°C. Éclairage LED intérieur. Compresseur silencieux et économe en énergie. Conforme aux normes HACCP.",
    category: "equipements",
    subcategory: "Froid professionnel",
    tags: ["réfrigérateur", "froid", "restauration", "professionnel"],
    brand: "CoolPro",
    manufacturer: "CoolPro Industries",
    status: "approved",
    is_active: true,
    is_new: true,
    unit_type: "piece",
    unit_label: "unité",
    dimensions: {
      length_cm: 60,
      width_cm: 65,
      height_cm: 185,
      volume_l: 400
    },
    weight: {
      net_weight_kg: 85,
      gross_weight_kg: 95
    },
    pricing: {
      price_ht_cents: 125000,
      currency: "EUR",
      tva_rate: 20
    },
    stock: {
      quantity_available: 12,
      quantity_reserved: 2,
      quantity_incoming: 10,
      reorder_threshold: 5
    },
    technical_specs: {
      material: "Inox 304",
      color: "Inox brossé",
      capacity: "400 litres",
      power_watts: 180,
      voltage: "220-240V",
      frequency_hz: 50,
      temperature_resistance_c: -5,
      norms: ["CE", "NF", "HACCP"],
      certifications: ["ISO 9001"],
      custom_specs: {
        "Classe énergétique": "A++",
        "Niveau sonore": "42 dB",
        "Gaz réfrigérant": "R600a",
        "Nombre d'étagères": "4"
      }
    },
    warranty: {
      duration_months: 24,
      warranty_type: "pièces et main d'œuvre",
      coverage: "Tous défauts de fabrication",
      manufacturer_warranty: true
    },
    compliance: {
      ce_marking: true,
      nf_marking: true,
      haccp_compliant: true,
      rohs_compliant: true
    },
    media: {
      technical_sheet_url: "/docs/frigo-400l-fiche-technique.pdf",
      user_manual_url: "/docs/frigo-400l-manuel.pdf"
    },
    logistics: {
      customs_code: "8418500000",
      is_stackable: false,
      is_fragile: true,
      lead_time_days: 5,
      min_order_quantity: 1,
      order_multiple: 1,
      available_zones: ["GUADELOUPE", "MARTINIQUE", "REUNION"]
    },
    vendor_id: "vendor_002",
    vendor_name: "EquipPro Caraïbes"
  },
  
  materiaux: {
    id: "prod_mat_001",
    sku: "KDM-CARREL-60",
    ean: "3760055544436",
    manufacturer_ref: "CR-60X60-ANT",
    name: "Carrelage Sol Antidérapant 60x60",
    short_description: "Carrelage grès cérame antidérapant, idéal zones humides",
    description: "Carrelage sol en grès cérame émaillé avec traitement antidérapant R10. Résistance exceptionnelle à l'usure et aux chocs. Idéal pour cuisines professionnelles, zones de passage intense et espaces extérieurs couverts.",
    category: "materiaux",
    subcategory: "Revêtements de sol",
    tags: ["carrelage", "sol", "antidérapant", "professionnel"],
    brand: "CeramPro",
    manufacturer: "CeramPro Italie",
    status: "approved",
    is_active: true,
    unit_type: "m²",
    unit_label: "m² (boîte de 1.44m²)",
    dimensions: {
      length_cm: 60,
      width_cm: 60,
      height_cm: 1
    },
    weight: {
      net_weight_kg: 24,
      unit_weight_kg: 6
    },
    pricing: {
      price_ht_cents: 3500,
      currency: "EUR",
      tva_rate: 20,
      tier_pricing: [
        { min_qty: 50, price_ht_cents: 3200 },
        { min_qty: 100, price_ht_cents: 2900 }
      ]
    },
    stock: {
      quantity_available: 850,
      quantity_reserved: 120,
      quantity_incoming: 500
    },
    packaging: {
      unit_per_pack: 4,
      pack_per_carton: 1,
      carton_per_pallet: 40,
      packaging_type: "carton",
      is_recyclable: true
    },
    origin: {
      country_code: "IT",
      country_name: "Italie",
      region: "Émilie-Romagne"
    },
    technical_specs: {
      material: "Grès cérame émaillé",
      composition: "Argile, feldspath, kaolin",
      color: "Gris anthracite",
      finish: "Mat antidérapant R10",
      norms: ["CE", "NF EN 14411"],
      certifications: ["UPEC U4P4E3C2"],
      custom_specs: {
        "Résistance au gel": "Oui",
        "Classe antidérapance": "R10",
        "Résistance flexion": "> 35 N/mm²",
        "Absorption eau": "< 0.5%",
        "Épaisseur": "10 mm"
      }
    },
    compliance: {
      ce_marking: true,
      reach_compliant: true
    },
    logistics: {
      customs_code: "6907210000",
      is_stackable: true,
      max_stack_height: 3,
      is_fragile: true,
      lead_time_days: 7,
      min_order_quantity: 10,
      order_multiple: 1,
      available_zones: ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION"]
    },
    vendor_id: "vendor_003",
    vendor_name: "MatPro Antilles"
  },
  
  chimie: {
    id: "prod_chim_001",
    sku: "KDM-DESINF-5L",
    ean: "3760077788894",
    manufacturer_ref: "DS-PRO-5L",
    name: "Désinfectant Surfaces Professionnel 5L",
    short_description: "Désinfectant virucide et bactéricide conforme EN 14476",
    description: "Solution désinfectante professionnelle prête à l'emploi. Action virucide, bactéricide et fongicide. Efficace en 5 minutes. Sans rinçage sur surfaces alimentaires. Conforme aux normes EN 14476 (virus) et EN 1276 (bactéries).",
    category: "chimie",
    subcategory: "Désinfection",
    tags: ["désinfectant", "hygiène", "HACCP", "professionnel"],
    brand: "HygienePro",
    manufacturer: "HygienePro France",
    status: "approved",
    is_active: true,
    unit_type: "L",
    unit_label: "bidon de 5L",
    dimensions: {
      length_cm: 15,
      width_cm: 15,
      height_cm: 30,
      volume_l: 5
    },
    weight: {
      net_weight_kg: 5.1,
      gross_weight_kg: 5.4
    },
    pricing: {
      price_ht_cents: 2450,
      currency: "EUR",
      tva_rate: 20,
      tier_pricing: [
        { min_qty: 10, price_ht_cents: 2200 },
        { min_qty: 50, price_ht_cents: 1950 }
      ]
    },
    stock: {
      quantity_available: 320,
      quantity_reserved: 40,
      quantity_incoming: 200
    },
    packaging: {
      unit_per_pack: 1,
      pack_per_carton: 4,
      carton_per_pallet: 80,
      packaging_type: "bidon PEHD",
      is_recyclable: true
    },
    origin: {
      country_code: "FR",
      country_name: "France",
      region: "Normandie"
    },
    technical_specs: {
      composition: "Ammoniums quaternaires, tensioactifs non ioniques",
      custom_specs: {
        "pH": "7.5 - 8.5",
        "Densité": "1.01 g/cm³",
        "Temps de contact": "5 minutes",
        "Dilution": "Prêt à l'emploi"
      }
    },
    compliance: {
      ce_marking: false,
      haccp_compliant: true,
      reach_compliant: true,
      hazard_class: "irritant",
      safety_data_sheet_url: "/docs/fds-desinfectant-5l.pdf"
    },
    media: {
      technical_sheet_url: "/docs/desinfectant-fiche-technique.pdf"
    },
    logistics: {
      customs_code: "3808940000",
      is_stackable: true,
      is_fragile: false,
      requires_adr: false,
      lead_time_days: 3,
      min_order_quantity: 4,
      order_multiple: 4,
      available_zones: ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "MAYOTTE"]
    },
    vendor_id: "vendor_004",
    vendor_name: "ChimPro Distribution"
  }
};

export default function ProductCardDemoPage() {
  const [activeCategory, setActiveCategory] = useState('alimentaire');
  
  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(7,10,16,0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)'
        }}
      >
        <div className="max-w-[1400px] mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Retour</span>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                <Package className="w-5 h-5 text-[#D9B35A]" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Fiche Produit Professionnelle</h1>
                <p className="text-xs text-white/50">Modèle multi-catégories</p>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      <div className="max-w-[1400px] mx-auto px-5 py-6">
        {/* Category Selector */}
        <div className="mb-6">
          <p className="text-white/60 text-sm mb-3">Sélectionnez une catégorie de produit :</p>
          <Tabs value={activeCategory} onValueChange={setActiveCategory}>
            <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl flex-wrap h-auto">
              <TabsTrigger 
                value="alimentaire" 
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Utensils className="w-4 h-4 mr-2" />
                Alimentaire
              </TabsTrigger>
              <TabsTrigger 
                value="equipements"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Wrench className="w-4 h-4 mr-2" />
                Équipements
              </TabsTrigger>
              <TabsTrigger 
                value="materiaux"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Factory className="w-4 h-4 mr-2" />
                Matériaux
              </TabsTrigger>
              <TabsTrigger 
                value="chimie"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Droplets className="w-4 h-4 mr-2" />
                Chimie
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        
        {/* Product Card */}
        <div className="glass-panel-soft rounded-[18px] p-6">
          <ProductCardView product={DEMO_PRODUCTS[activeCategory]} />
        </div>
      </div>
    </div>
  );
}
