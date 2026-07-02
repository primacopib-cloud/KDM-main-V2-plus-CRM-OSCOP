import React, { useState, useEffect } from 'react';
import {
  Package, Tag, Building2, MapPin, Scale, Ruler, Thermometer, X,
  Clock, Shield, FileText, Truck, Box, Leaf, Award, AlertTriangle,
  ChevronDown, ChevronUp, Save, Plus, Trash2, Upload, Info, Zap, Wrench,
  Droplets, Globe, CheckCircle2, Eye, Search, Filter, Edit, MoreVertical
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Checkbox } from './ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from './ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Country flags SVG component
const CountryFlag = ({ countryCode, size = 24 }) => {
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
  };
  
  return flags[countryCode] || (
    <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
      <rect width="900" height="600" fill="#cccccc"/>
      <text x="450" y="320" textAnchor="middle" fontSize="200" fill="#666666">{countryCode}</text>
    </svg>
  );
};

// Categories
const CATEGORIES = [
  { value: 'alimentaire', label: 'Alimentaire', icon: '🍎' },
  { value: 'boissons', label: 'Boissons', icon: '🥤' },
  { value: 'materiaux', label: 'Matériaux', icon: '🧱' },
  { value: 'equipements', label: 'Équipements', icon: '⚙️' },
  { value: 'matieres_premieres', label: 'Matières premières', icon: '🪨' },
  { value: 'hygiene', label: 'Hygiène', icon: '🧴' },
  { value: 'chimie', label: 'Chimie', icon: '🧪' },
  { value: 'textile', label: 'Textile', icon: '👕' },
  { value: 'electronique', label: 'Électronique', icon: '💻' },
  { value: 'autre', label: 'Autre', icon: '📦' }
];

// Units
const UNITS = [
  { value: 'piece', label: 'Pièce' },
  { value: 'kg', label: 'Kilogramme (kg)' },
  { value: 'g', label: 'Gramme (g)' },
  { value: 'L', label: 'Litre (L)' },
  { value: 'mL', label: 'Millilitre (mL)' },
  { value: 'm', label: 'Mètre (m)' },
  { value: 'cm', label: 'Centimètre (cm)' },
  { value: 'm²', label: 'Mètre carré (m²)' },
  { value: 'm³', label: 'Mètre cube (m³)' },
  { value: 'T', label: 'Tonne (T)' },
  { value: 'palette', label: 'Palette' },
  { value: 'carton', label: 'Carton' },
  { value: 'lot', label: 'Lot' }
];

// TVA rates
const TVA_RATES = [
  { value: 0, label: '0% (Exonéré)' },
  { value: 2.1, label: '2.1% (Presse)' },
  { value: 5.5, label: '5.5% (Alimentaire)' },
  { value: 10, label: '10% (Restauration)' },
  { value: 20, label: '20% (Standard)' }
];

// Temperature ranges
const TEMP_RANGES = [
  { value: 'ambient', label: 'Température ambiante (15-25°C)' },
  { value: 'refrigerated', label: 'Réfrigéré (0-4°C)' },
  { value: 'frozen', label: 'Surgelé (-18°C)' },
  { value: 'deep_frozen', label: 'Surgélation profonde (-25°C)' },
  { value: 'controlled', label: 'Température contrôlée' }
];

// Countries
const COUNTRIES = [
  { code: 'FR', name: 'France' },
  { code: 'ES', name: 'Espagne' },
  { code: 'IT', name: 'Italie' },
  { code: 'DE', name: 'Allemagne' },
  { code: 'BE', name: 'Belgique' },
  { code: 'NL', name: 'Pays-Bas' },
  { code: 'PT', name: 'Portugal' },
  { code: 'MA', name: 'Maroc' },
  { code: 'TN', name: 'Tunisie' },
  { code: 'CN', name: 'Chine' },
  { code: 'TH', name: 'Thaïlande' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'IN', name: 'Inde' },
  { code: 'BR', name: 'Brésil' },
  { code: 'US', name: 'États-Unis' }
];

// Zones
const ZONES = [
  { code: 'GUADELOUPE', name: 'Guadeloupe' },
  { code: 'MARTINIQUE', name: 'Martinique' },
  { code: 'GUYANE', name: 'Guyane' },
  { code: 'REUNION', name: 'La Réunion' },
  { code: 'MAYOTTE', name: 'Mayotte' }
];

// Allergens
const ALLERGENS = [
  'gluten', 'crustacés', 'oeufs', 'poissons', 'arachides',
  'soja', 'lait', 'fruits à coque', 'céleri', 'moutarde',
  'sésame', 'sulfites', 'lupin', 'mollusques'
];

// Default empty product
const getEmptyProduct = (category = 'alimentaire') => ({
  sku: '',
  ean: '',
  manufacturer_ref: '',
  name: '',
  short_description: '',
  description: '',
  category: category,
  subcategory: '',
  tags: [],
  brand: '',
  manufacturer: '',
  status: 'draft',
  is_active: true,
  is_new: false,
  is_featured: false,
  unit_type: category === 'alimentaire' ? 'kg' : 'piece',
  unit_label: '',
  // Pricing
  price_ht_cents: 0,
  tva_rate: category === 'alimentaire' ? 5.5 : 20,
  // Dimensions
  length_cm: '',
  width_cm: '',
  height_cm: '',
  volume_l: '',
  // Weight
  net_weight_kg: '',
  gross_weight_kg: '',
  // Origin
  country_code: 'FR',
  region: '',
  producer_name: '',
  // Packaging
  unit_per_pack: 1,
  pack_per_carton: '',
  carton_per_pallet: '',
  packaging_type: '',
  is_recyclable: false,
  // Conservation (food)
  temperature_range: 'ambient',
  shelf_life_days: '',
  dlc_type: 'DDM',
  storage_instructions: '',
  // Nutrition (food)
  energy_kcal: '',
  fat_g: '',
  carbohydrates_g: '',
  protein_g: '',
  salt_g: '',
  nutri_score: '',
  // Allergens
  allergens_contains: [],
  allergens_may_contain: [],
  // Ingredients
  ingredients: '',
  // Technical specs (equipment/materials)
  material: '',
  power_watts: '',
  voltage: '',
  norms: [],
  // Warranty
  warranty_months: 12,
  // Compliance
  ce_marking: false,
  haccp_compliant: false,
  organic_certified: false,
  reach_compliant: false,
  // Logistics
  lead_time_days: 3,
  min_order_quantity: 1,
  available_zones: ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE'],
  is_fragile: false,
  requires_adr: false
});

// Section wrapper
const FormSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-white/[0.08] rounded-xl overflow-hidden mb-4">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-3 flex items-center justify-between bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-[#D9B35A]" />}
          <span className="font-medium text-white text-sm">{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>
      {isOpen && (
        <div className="p-4 space-y-4 border-t border-white/[0.08]">
          {children}
        </div>
      )}
    </div>
  );
};

// Tag input component
const TagInput = ({ value = [], onChange, placeholder }) => {
  const [input, setInput] = useState('');
  
  const addTag = () => {
    if (input.trim() && !value.includes(input.trim())) {
      onChange([...value, input.trim()]);
      setInput('');
    }
  };
  
  const removeTag = (tag) => {
    onChange(value.filter(t => t !== tag));
  };
  
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
          placeholder={placeholder}
          className="flex-1 bg-white/[0.04] border-white/10 text-white text-sm"
        />
        <Button type="button" size="sm" onClick={addTag} variant="outline" className="border-white/10">
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((tag) => (
            <Badge key={`tag-${tag}`} variant="outline" className="bg-white/[0.04] border-white/10 text-xs">
              {tag}
              <button type="button" onClick={() => removeTag(tag)} className="ml-1 hover:text-red-400">
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

// Main Form Component
export default function ProductCatalogManager({ onProductSaved }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState(getEmptyProduct());
  const [activeTab, setActiveTab] = useState('basic');
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Fetch products
  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.products || []);
      }
    } catch (err) {
      console.error('Error fetching products:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  // Handle form changes
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Open form for new product
  const openNewProduct = () => {
    setEditingProduct(null);
    setFormData(getEmptyProduct());
    setActiveTab('basic');
    setIsFormOpen(true);
  };

  // Open form for editing
  const openEditProduct = (product) => {
    setEditingProduct(product);
    setFormData({
      ...getEmptyProduct(product.category),
      ...product,
      price_ht_cents: product.pricing?.price_ht_cents || 0,
      tva_rate: product.pricing?.tva_rate || 20,
      country_code: product.origin?.country_code || 'FR',
      region: product.origin?.region || '',
      producer_name: product.origin?.producer_name || '',
      length_cm: product.dimensions?.length_cm || '',
      width_cm: product.dimensions?.width_cm || '',
      height_cm: product.dimensions?.height_cm || '',
      volume_l: product.dimensions?.volume_l || '',
      net_weight_kg: product.weight?.net_weight_kg || '',
      gross_weight_kg: product.weight?.gross_weight_kg || '',
      unit_per_pack: product.packaging?.unit_per_pack || 1,
      pack_per_carton: product.packaging?.pack_per_carton || '',
      carton_per_pallet: product.packaging?.carton_per_pallet || '',
      packaging_type: product.packaging?.packaging_type || '',
      is_recyclable: product.packaging?.is_recyclable || false,
      temperature_range: product.conservation?.temperature_range || 'ambient',
      shelf_life_days: product.conservation?.shelf_life_days || '',
      dlc_type: product.conservation?.dlc_type || 'DDM',
      storage_instructions: product.conservation?.storage_instructions || '',
      energy_kcal: product.nutrition?.energy_kcal || '',
      fat_g: product.nutrition?.fat_g || '',
      carbohydrates_g: product.nutrition?.carbohydrates_g || '',
      protein_g: product.nutrition?.protein_g || '',
      salt_g: product.nutrition?.salt_g || '',
      nutri_score: product.nutrition?.nutri_score || '',
      allergens_contains: product.allergens?.contains || [],
      allergens_may_contain: product.allergens?.may_contain || [],
      material: product.technical_specs?.material || '',
      power_watts: product.technical_specs?.power_watts || '',
      voltage: product.technical_specs?.voltage || '',
      norms: product.technical_specs?.norms || [],
      warranty_months: product.warranty?.duration_months || 12,
      ce_marking: product.compliance?.ce_marking || false,
      haccp_compliant: product.compliance?.haccp_compliant || false,
      organic_certified: product.compliance?.organic_certified || false,
      reach_compliant: product.compliance?.reach_compliant || false,
      lead_time_days: product.logistics?.lead_time_days || 3,
      min_order_quantity: product.logistics?.min_order_quantity || 1,
      available_zones: product.logistics?.available_zones || ZONES.map(z => z.code),
      is_fragile: product.logistics?.is_fragile || false,
      requires_adr: product.logistics?.requires_adr || false
    });
    setActiveTab('basic');
    setIsFormOpen(true);
  };

  // Save product
  const handleSave = async () => {
    if (!formData.sku || !formData.name) {
      toast.error('SKU et Nom sont requis');
      return;
    }

    setSaving(true);
    try {
      // Build product object
      const productData = {
        sku: formData.sku,
        ean: formData.ean || null,
        manufacturer_ref: formData.manufacturer_ref || null,
        name: formData.name,
        short_description: formData.short_description || null,
        description: formData.description || null,
        category: formData.category,
        subcategory: formData.subcategory || null,
        tags: formData.tags || [],
        brand: formData.brand || null,
        manufacturer: formData.manufacturer || null,
        status: formData.status,
        is_active: formData.is_active,
        is_new: formData.is_new,
        is_featured: formData.is_featured,
        unit_type: formData.unit_type,
        unit_label: formData.unit_label || null,
        pricing: {
          price_ht_cents: parseInt(formData.price_ht_cents) || 0,
          currency: 'EUR',
          tva_rate: parseFloat(formData.tva_rate) || 20
        },
        dimensions: {
          length_cm: parseFloat(formData.length_cm) || null,
          width_cm: parseFloat(formData.width_cm) || null,
          height_cm: parseFloat(formData.height_cm) || null,
          volume_l: parseFloat(formData.volume_l) || null
        },
        weight: {
          net_weight_kg: parseFloat(formData.net_weight_kg) || null,
          gross_weight_kg: parseFloat(formData.gross_weight_kg) || null
        },
        origin: {
          country_code: formData.country_code,
          country_name: COUNTRIES.find(c => c.code === formData.country_code)?.name || '',
          region: formData.region || null,
          producer_name: formData.producer_name || null
        },
        packaging: {
          unit_per_pack: parseInt(formData.unit_per_pack) || 1,
          pack_per_carton: parseInt(formData.pack_per_carton) || null,
          carton_per_pallet: parseInt(formData.carton_per_pallet) || null,
          packaging_type: formData.packaging_type || null,
          is_recyclable: formData.is_recyclable
        },
        ingredients: formData.ingredients || null,
        logistics: {
          lead_time_days: parseInt(formData.lead_time_days) || 3,
          min_order_quantity: parseInt(formData.min_order_quantity) || 1,
          available_zones: formData.available_zones || [],
          is_fragile: formData.is_fragile,
          requires_adr: formData.requires_adr
        }
      };

      // Add food-specific fields
      if (['alimentaire', 'boissons'].includes(formData.category)) {
        productData.conservation = {
          temperature_range: formData.temperature_range,
          shelf_life_days: parseInt(formData.shelf_life_days) || null,
          dlc_type: formData.dlc_type,
          storage_instructions: formData.storage_instructions || null
        };
        productData.nutrition = {
          energy_kcal: parseFloat(formData.energy_kcal) || null,
          fat_g: parseFloat(formData.fat_g) || null,
          carbohydrates_g: parseFloat(formData.carbohydrates_g) || null,
          protein_g: parseFloat(formData.protein_g) || null,
          salt_g: parseFloat(formData.salt_g) || null,
          nutri_score: formData.nutri_score || null
        };
        productData.allergens = {
          contains: formData.allergens_contains || [],
          may_contain: formData.allergens_may_contain || []
        };
      }

      // Add equipment-specific fields
      if (['equipements', 'electronique', 'materiaux'].includes(formData.category)) {
        productData.technical_specs = {
          material: formData.material || null,
          power_watts: parseFloat(formData.power_watts) || null,
          voltage: formData.voltage || null,
          norms: formData.norms || []
        };
        productData.warranty = {
          duration_months: parseInt(formData.warranty_months) || 12
        };
      }

      // Add compliance
      productData.compliance = {
        ce_marking: formData.ce_marking,
        haccp_compliant: formData.haccp_compliant,
        organic_certified: formData.organic_certified,
        reach_compliant: formData.reach_compliant
      };

      const url = editingProduct 
        ? `${API_URL}/api/catalog/admin/products/${editingProduct.id}`
        : `${API_URL}/api/catalog/admin/products`;
      
      const method = editingProduct ? 'PUT' : 'POST';
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(productData)
      });

      if (res.ok) {
        toast.success(editingProduct ? 'Produit mis à jour' : 'Produit créé');
        setIsFormOpen(false);
        fetchProducts();
        if (onProductSaved) onProductSaved();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      toast.error('Erreur de connexion');
    } finally {
      setSaving(false);
    }
  };

  // Delete product
  const handleDelete = async (productId) => {
    if (!confirm('Supprimer ce produit ?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products/${productId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        toast.success('Produit supprimé');
        fetchProducts();
      }
    } catch (err) {
      toast.error('Erreur de suppression');
    }
  };

  // Filter products
  const filteredProducts = products.filter(p => {
    const matchesSearch = !searchTerm || 
      p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.sku?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || p.category === categoryFilter;
    const matchesStatus = statusFilter === 'all' || p.status === statusFilter;
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const isFood = ['alimentaire', 'boissons'].includes(formData.category);
  const isEquipment = ['equipements', 'electronique', 'materiaux'].includes(formData.category);

  // Format price
  const formatPrice = (cents) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format((cents || 0) / 100);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Package className="w-5 h-5 text-[#D9B35A]" />
            Catalogue Produits
          </h2>
          <p className="text-sm text-white/50">{products.length} produits</p>
        </div>
        <Button onClick={openNewProduct} className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
          <Plus className="w-4 h-4 mr-2" />
          Nouveau produit
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
          <Input
            placeholder="Rechercher par nom ou SKU..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 bg-white/[0.04] border-white/10 text-white"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px] bg-white/[0.04] border-white/10">
            <SelectValue placeholder="Catégorie" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes catégories</SelectItem>
            {CATEGORIES.map(c => (
              <SelectItem key={c.value} value={c.value}>{c.icon} {c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px] bg-white/[0.04] border-white/10">
            <SelectValue placeholder="Statut" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous statuts</SelectItem>
            <SelectItem value="draft">Brouillon</SelectItem>
            <SelectItem value="approved">Approuvé</SelectItem>
            <SelectItem value="pending_approval">En attente</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Products List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 text-white/50">Chargement...</div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-12 text-white/50">
            <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Aucun produit trouvé</p>
            <Button onClick={openNewProduct} variant="outline" className="mt-4 border-white/10">
              Créer un produit
            </Button>
          </div>
        ) : (
          filteredProducts.map(product => (
            <div 
              key={product.id}
              className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center gap-4 hover:bg-white/[0.04] transition-colors"
            >
              {/* Image placeholder */}
              <div className="w-16 h-16 rounded-xl bg-white/[0.04] flex items-center justify-center flex-shrink-0">
                <Package className="w-6 h-6 text-white/20" />
              </div>
              
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs">{CATEGORIES.find(c => c.value === product.category)?.icon}</span>
                  <p className="font-semibold text-white truncate">{product.name}</p>
                  {product.is_new && <Badge className="bg-blue-500/20 text-blue-400 border-0 text-xs">Nouveau</Badge>}
                </div>
                <div className="flex items-center gap-3 text-xs text-white/50">
                  <span className="font-mono">{product.sku}</span>
                  {product.ean && <span>EAN: {product.ean}</span>}
                  <span>{product.brand}</span>
                </div>
              </div>
              
              {/* Price */}
              <div className="text-right">
                <p className="font-bold text-[#D9B35A]">{formatPrice(product.pricing?.price_ht_cents)}</p>
                <p className="text-xs text-white/50">HT · TVA {product.pricing?.tva_rate}%</p>
              </div>
              
              {/* Status */}
              <Badge 
                variant="outline" 
                className={
                  product.status === 'approved' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                  product.status === 'draft' ? 'bg-gray-500/20 text-gray-400 border-gray-500/30' :
                  'bg-amber-500/20 text-amber-400 border-amber-500/30'
                }
              >
                {product.status === 'approved' ? 'Approuvé' : product.status === 'draft' ? 'Brouillon' : 'En attente'}
              </Badge>
              
              {/* Actions */}
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => openEditProduct(product)} className="text-white/60 hover:text-white">
                  <Edit className="w-4 h-4" />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => handleDelete(product.id)} className="text-white/60 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Product Form Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-[#0a0d14] border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-[#D9B35A]" />
              {editingProduct ? 'Modifier le produit' : 'Nouveau produit'}
            </DialogTitle>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl mb-4">
              <TabsTrigger value="basic" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg text-xs">
                Informations
              </TabsTrigger>
              <TabsTrigger value="pricing" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg text-xs">
                Prix & Stock
              </TabsTrigger>
              {isFood && (
                <TabsTrigger value="food" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg text-xs">
                  Alimentaire
                </TabsTrigger>
              )}
              {isEquipment && (
                <TabsTrigger value="technical" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg text-xs">
                  Technique
                </TabsTrigger>
              )}
              <TabsTrigger value="logistics" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg text-xs">
                Logistique
              </TabsTrigger>
            </TabsList>

            {/* Basic Info Tab */}
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

            {/* Pricing Tab */}
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

            {/* Food Tab */}
            {isFood && (
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
            )}

            {/* Technical Tab */}
            {isEquipment && (
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
            )}

            {/* Logistics Tab */}
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
          </Tabs>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setIsFormOpen(false)} className="border-white/10">
              Annuler
            </Button>
            <Button onClick={handleSave} disabled={saving} className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
              {saving ? 'Enregistrement...' : (editingProduct ? 'Mettre à jour' : 'Créer le produit')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
