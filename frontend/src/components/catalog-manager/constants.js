// Categories
export const CATEGORIES = [
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
export const UNITS = [
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
export const TVA_RATES = [
  { value: 0, label: '0% (Exonéré)' },
  { value: 2.1, label: '2.1% (Presse)' },
  { value: 5.5, label: '5.5% (Alimentaire)' },
  { value: 10, label: '10% (Restauration)' },
  { value: 20, label: '20% (Standard)' }
];

// Temperature ranges
export const TEMP_RANGES = [
  { value: 'ambient', label: 'Température ambiante (15-25°C)' },
  { value: 'refrigerated', label: 'Réfrigéré (0-4°C)' },
  { value: 'frozen', label: 'Surgelé (-18°C)' },
  { value: 'deep_frozen', label: 'Surgélation profonde (-25°C)' },
  { value: 'controlled', label: 'Température contrôlée' }
];

// Countries
export const COUNTRIES = [
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
export const ZONES = [
  { code: 'GUADELOUPE', name: 'Guadeloupe' },
  { code: 'MARTINIQUE', name: 'Martinique' },
  { code: 'GUYANE', name: 'Guyane' },
  { code: 'REUNION', name: 'La Réunion' },
  { code: 'MAYOTTE', name: 'Mayotte' }
];

// Allergens
export const ALLERGENS = [
  'gluten', 'crustacés', 'oeufs', 'poissons', 'arachides',
  'soja', 'lait', 'fruits à coque', 'céleri', 'moutarde',
  'sésame', 'sulfites', 'lupin', 'mollusques'
];

// Default empty product
export const getEmptyProduct = (category = 'alimentaire') => ({
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

export const formatPrice = (cents) => {
  return new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR' }).format((cents || 0) / 100);
};
