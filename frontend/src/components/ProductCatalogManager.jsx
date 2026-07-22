import React, { useState, useEffect } from 'react';
import {
  Package, Search, Plus, Trash2, Edit, Rocket, Sparkles,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from './ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from './ui/dialog';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import { CATEGORIES, ZONES, COUNTRIES, getEmptyProduct, formatPrice } from './catalog-manager/constants';
import { BasicTab, PricingTab } from './catalog-manager/BasicPricingTabs';
import { FoodTab, TechnicalTab, LogisticsTab } from './catalog-manager/SpecializedTabs';
import { AiProductAssistant } from './catalog-manager/AiProductAssistant';
import { BulkEanImport } from './catalog-manager/BulkEanImport';

const API_URL = process.env.REACT_APP_BACKEND_URL;

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
        image_url: formData.image_url || null,
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

  const [pricingId, setPricingId] = useState('');
  const [selected, setSelected] = useState([]);

  const toggleSelect = (id) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  const publishSelected = async () => {
    const res = await fetch(`${API_URL}/api/catalog/admin/products/publish-bulk`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: selected }),
    });
    const d = await res.json();
    if (!res.ok) return toast.error(d.detail || 'Publication échouée');
    toast.success(`${d.published} fiche(s) publiée(s) au catalogue ✓`);
    setSelected([]);
    fetchProducts();
  };

  const publishProduct = async (product) => {
    const res = await fetch(`${API_URL}/api/catalog/admin/products/${product.id}/publish`, {
      method: 'POST', credentials: 'include',
    });
    const d = await res.json();
    if (!res.ok) return toast.error(d.detail || 'Publication échouée');
    toast.success(`« ${product.name} » publié au catalogue ✓`);
    fetchProducts();
  };

  const suggestPrice = async (product) => {
    setPricingId(product.id);
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/products/${product.id}/ai-price`, {
        method: 'POST', credentials: 'include',
      });
      const d = await res.json();
      if (!res.ok) return toast.error(d.detail || 'Suggestion échouée');
      toast.success(`Prix suggéré : ${(d.price_ht_cents / 100).toFixed(2)} € HT — ${d.reason}`, { duration: 8000 });
      fetchProducts();
    } finally { setPricingId(''); }
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
        <div className="flex gap-2 flex-wrap">
          {selected.length > 0 && (
            <Button onClick={publishSelected} data-testid="publish-selected-btn"
              className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <Rocket className="w-4 h-4 mr-2" /> Publier la sélection ({selected.length})
            </Button>
          )}
          <BulkEanImport onDone={fetchProducts} />
          <Button onClick={openNewProduct} className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
            <Plus className="w-4 h-4 mr-2" />
            Nouveau produit
          </Button>
        </div>
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
              {/* Sélection (brouillons) */}
              {product.status === 'draft' && (
                <input type="checkbox" checked={selected.includes(product.id)} onChange={() => toggleSelect(product.id)}
                  data-testid={`product-select-${product.id}`}
                  className="w-4 h-4 accent-[#D9B35A] flex-shrink-0 cursor-pointer" />
              )}
              {/* Image */}
              <div className="w-16 h-16 rounded-xl bg-white/[0.04] flex items-center justify-center flex-shrink-0 overflow-hidden">
                {product.image_url
                  ? <img src={`${API_URL}${product.image_url}`} alt={product.name} className="w-full h-full object-cover" />
                  : <Package className="w-6 h-6 text-white/20" />}
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
                {product.status === 'draft' && (
                  <>
                    <Button size="sm" onClick={() => suggestPrice(product)} disabled={pricingId === product.id}
                      data-testid={`product-ai-price-${product.id}`} title="Prix suggéré par l'IA (marché Outre-mer)"
                      className="bg-white/[0.06] border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/15 h-8 px-2 text-xs">
                      <Sparkles className={`w-3.5 h-3.5 mr-1 ${pricingId === product.id ? 'animate-spin' : ''}`} /> Prix IA
                    </Button>
                    <Button size="sm" onClick={() => publishProduct(product)}
                      data-testid={`product-publish-${product.id}`} title="Publier cette fiche au catalogue"
                      className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black h-8 px-2 text-xs font-bold">
                      <Rocket className="w-3.5 h-3.5 mr-1" /> Publier
                    </Button>
                  </>
                )}
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

          <AiProductAssistant formData={formData}
            onApply={(fields) => setFormData((prev) => ({ ...prev, ...fields }))} />

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
            <BasicTab formData={formData} handleChange={handleChange} />
            <PricingTab formData={formData} handleChange={handleChange} />
            {isFood && <FoodTab formData={formData} handleChange={handleChange} />}
            {isEquipment && <TechnicalTab formData={formData} handleChange={handleChange} />}
            <LogisticsTab formData={formData} handleChange={handleChange} />
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
