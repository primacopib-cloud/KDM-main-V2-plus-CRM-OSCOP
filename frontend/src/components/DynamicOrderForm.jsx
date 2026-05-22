import React, { useState, useEffect, useMemo } from 'react';
import Barcode from 'react-barcode';
import { 
  Package, Truck, FileText, Building2, Calendar, MapPin, 
  CheckCircle2, AlertCircle, Plus, Minus, RefreshCw, Info
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { legalVariables, replaceVariables } from '../data/legalDocuments';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Dynamic Purchase Order Component with Zone-based Preparation Options
const DynamicOrderForm = ({ 
  orderData = {},
  products = [],
  zoneCode = 'GUADELOUPE',
  signatureData = {
    clientName: '',
    clientTitle: '',
    signatureDate: new Date().toLocaleDateString('fr-FR'),
    signatureLocation: ''
  },
  showStamp = true,
  onTotalsChange,
  onPreparationChange
}) => {
  const [preparationOptions, setPreparationOptions] = useState([]);
  const [selectedOptions, setSelectedOptions] = useState({});
  const [quantities, setQuantities] = useState({});
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [calculatedTotals, setCalculatedTotals] = useState(null);
  const [error, setError] = useState(null);
  const [zoneInfo, setZoneInfo] = useState(null);

  // Merge order data with default variables
  const vars = { ...legalVariables, ...orderData, ZONE_CODE: zoneCode };

  // Format currency
  const formatCurrency = (amountCents) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR' 
    }).format((amountCents || 0) / 100);
  };

  // Get zone TVA rate (default 8.5%, 0% for exonerated zones)
  const zoneTvaRate = useMemo(() => {
    if (zoneInfo?.vat_rate !== undefined) {
      return zoneInfo.vat_rate;
    }
    // Default rates by zone
    const exoneratedZones = ['GUYANE', 'MAYOTTE'];
    return exoneratedZones.includes(zoneCode) ? 0 : 8.5;
  }, [zoneCode, zoneInfo]);

  const isVatExonerated = zoneTvaRate === 0;

  // Calculate products subtotal
  const productsSubtotalHT = useMemo(() => {
    return products.reduce((sum, p) => sum + (p.total_ht || p.unit_price_ht * p.qty || 0), 0) * 100;
  }, [products]);

  const productsTVA = useMemo(() => {
    if (isVatExonerated) return 0;
    return Math.round(productsSubtotalHT * zoneTvaRate / 100);
  }, [productsSubtotalHT, zoneTvaRate, isVatExonerated]);

  // Fetch zone info and preparation options
  useEffect(() => {
    const fetchZoneData = async () => {
      if (!zoneCode) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch zone info
        try {
          const zoneResponse = await fetch(`${API_URL}/api/admin/v1/zones/${zoneCode}`);
          if (zoneResponse.ok) {
            const zoneData = await zoneResponse.json();
            setZoneInfo(zoneData);
          }
        } catch (e) {
          console.log('Zone info not available, using defaults');
        }

        // Fetch preparation options
        const response = await fetch(`${API_URL}/api/v2/preparation/options/${zoneCode}`);
        if (!response.ok) {
          if (response.status === 404) {
            setPreparationOptions([]);
            return;
          }
          throw new Error('Erreur lors du chargement des options');
        }
        const data = await response.json();
        setPreparationOptions(data);
        
        // Auto-select default options
        const defaults = {};
        const defaultQty = {};
        data.forEach(opt => {
          if (opt.is_default || opt.is_required) {
            defaults[opt.id] = true;
            defaultQty[opt.id] = 1;
          }
        });
        setSelectedOptions(defaults);
        setQuantities(defaultQty);
      } catch (err) {
        console.error('Error fetching preparation options:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchZoneData();
  }, [zoneCode]);

  // Calculate totals when selections change
  useEffect(() => {
    const calculateTotals = async () => {
      if (!zoneCode || productsSubtotalHT === 0) return;
      
      setCalculating(true);
      
      try {
        const selections = Object.entries(selectedOptions)
          .filter(([_, selected]) => selected)
          .map(([optionId]) => ({
            option_id: optionId,
            quantity: quantities[optionId] || 1
          }));

        const response = await fetch(`${API_URL}/api/v2/preparation/calculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            products_subtotal_ht_cents: productsSubtotalHT,
            products_tva_cents: productsTVA,
            zone_code: zoneCode,
            preparation_selections: selections
          })
        });

        if (!response.ok) throw new Error('Erreur de calcul');
        
        const totals = await response.json();
        setCalculatedTotals(totals);
        
        if (onTotalsChange) {
          onTotalsChange(totals);
        }
        if (onPreparationChange) {
          onPreparationChange(totals.preparation_details);
        }
      } catch (err) {
        console.error('Calculation error:', err);
      } finally {
        setCalculating(false);
      }
    };

    const debounce = setTimeout(calculateTotals, 300);
    return () => clearTimeout(debounce);
  }, [selectedOptions, quantities, productsSubtotalHT, productsTVA, zoneCode, onTotalsChange, onPreparationChange]);

  // Toggle option selection
  const toggleOption = (optionId, isRequired) => {
    if (isRequired) return;
    
    setSelectedOptions(prev => ({
      ...prev,
      [optionId]: !prev[optionId]
    }));
    
    if (!selectedOptions[optionId]) {
      setQuantities(prev => ({ ...prev, [optionId]: 1 }));
    }
  };

  // Update quantity
  const updateQuantity = (optionId, delta) => {
    setQuantities(prev => {
      const current = prev[optionId] || 1;
      const option = preparationOptions.find(o => o.id === optionId);
      let newQty = current + delta;
      
      if (option?.min_qty && newQty < option.min_qty) {
        newQty = option.min_qty;
      }
      if (option?.max_qty && newQty > option.max_qty) {
        newQty = option.max_qty;
      }
      if (newQty < 1) newQty = 1;
      
      return { ...prev, [optionId]: newQty };
    });
  };

  // Get pricing mode label
  const getPricingModeLabel = (mode) => {
    switch (mode) {
      case 'FIXED': case 'ORDER': return 'Forfait';
      case 'PER_UNIT': case 'PALLET': return '/palette';
      case 'CARTON': return '/carton';
      case 'CONTAINER': return '/container';
      case 'PER_KG': return '/kg';
      case 'PERCENTAGE': return '%';
      default: return '';
    }
  };

  // Get preparation type icon color
  const getTypeColor = (type) => {
    switch (type) {
      case 'PREP_PALLET': case 'PALETTE': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'PREP_CARTON': case 'CARTON': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'PREP_CONTAINER': return 'bg-indigo-100 text-indigo-700 border-indigo-200';
      case 'MANUTENTION': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'EXPRESS': return 'bg-red-100 text-red-700 border-red-200';
      case 'STOCKAGE': return 'bg-gray-100 text-gray-700 border-gray-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  // Generate EAN-13 barcode from SKU
  const generateBarcode = (sku) => {
    if (!sku) return null;
    // Simple hash to generate 12-digit number for EAN-13
    let hash = 0;
    for (let i = 0; i < sku.length; i++) {
      hash = ((hash << 5) - hash) + sku.charCodeAt(i);
      hash = hash & hash;
    }
    const base = Math.abs(hash).toString().padStart(12, '0').slice(0, 12);
    // Calculate check digit for EAN-13
    let sum = 0;
    for (let i = 0; i < 12; i++) {
      sum += parseInt(base[i]) * (i % 2 === 0 ? 1 : 3);
    }
    const checkDigit = (10 - (sum % 10)) % 10;
    return base + checkDigit;
  };

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-xl text-gray-900 print:shadow-none" data-testid="dynamic-order-form">
      {/* Premium Header */}
      <header 
        className="relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 45%, #4a1776 100%)',
          padding: '32px'
        }}
      >
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `
              radial-gradient(circle at 20% 20%, rgba(212,175,55,0.26), transparent 55%),
              radial-gradient(circle at 70% 35%, rgba(242,208,122,0.18), transparent 58%)
            `
          }}
        />
        
        <div className="relative z-10">
          <div className="flex justify-between items-start flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div 
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ 
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.16)'
                }}
              >
                <Package className="w-8 h-8 text-[#d4af37]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">BON DE COMMANDE</h1>
                <p className="text-white/70 text-sm mt-1">
                  Vente B2B de marchandises — <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-[#d4af37]/20 text-[#f2d07a] border border-[#d4af37]/40">EXW</span>
                </p>
              </div>
            </div>
            
            <div className="text-right text-white/80 text-sm space-y-1">
              <p>Commande n° <span className="font-mono text-white">{replaceVariables(vars.COMMANDE_REF || 'BC-XXXX-XXXX', vars)}</span></p>
              <p>Date : <span className="font-mono text-white">{replaceVariables(vars.DATE_FACTURE || new Date().toLocaleDateString('fr-FR'), vars)}</span></p>
              <p>Zone : <span className="font-mono text-white font-bold">{zoneCode}</span></p>
              <p>TVA : <span className={`font-mono ${isVatExonerated ? 'text-emerald-400 font-bold' : 'text-white'}`}>
                {isVatExonerated ? 'Exonérée (0%)' : `${zoneTvaRate}%`}
              </span></p>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-2 mt-4">
            {[
              { icon: CheckCircle2, label: 'B2B uniquement', color: '#d4af37' },
              { icon: Truck, label: 'Incoterm EXW', color: '#d4af37' },
              { icon: MapPin, label: zoneCode, color: '#10b981' },
              ...(isVatExonerated ? [{ icon: CheckCircle2, label: 'TVA 0%', color: '#10b981' }] : []),
            ].map((tag, idx) => (
              <span 
                key={idx}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs text-white/90"
                style={{ 
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.14)'
                }}
              >
                <span className="w-2 h-2 rounded-full" style={{ background: tag.color }} />
                {tag.label}
              </span>
            ))}
          </div>
        </div>
      </header>

      <main className="p-8 space-y-6">
        {/* Parties Grid */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-[#b07a1a]" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Vendeur</h3>
            </div>
            <p className="font-bold text-gray-900">{replaceVariables(vars.KDM_LEGAL_NAME, vars)}</p>
            <p className="text-sm text-gray-600 mt-1">
              {replaceVariables(vars.KDM_FORM, vars)} — {replaceVariables(vars.KDM_ADDRESS, vars)}
            </p>
            <p className="text-sm text-gray-600">SIRET : {replaceVariables(vars.KDM_SIRET, vars)}</p>
            <p className="text-sm text-gray-600">TVA : {replaceVariables(vars.KDM_TVA, vars)}</p>
          </div>
          
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-[#4a1776]" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Acheteur (B2B)</h3>
            </div>
            <p className="font-bold text-gray-900">{replaceVariables(vars.CLIENT_LEGAL_NAME || '[Raison sociale]', vars)}</p>
            <p className="text-sm text-gray-600 mt-1">{replaceVariables(vars.CLIENT_ADDRESS || '[Adresse]', vars)}</p>
            <p className="text-sm text-gray-600">SIRET : {replaceVariables(vars.CLIENT_SIRET || '[SIRET]', vars)}</p>
            <p className="text-sm text-gray-600">Contact : {replaceVariables(vars.CLIENT_CONTACT || '[Contact]', vars)}</p>
          </div>
        </div>

        {/* EXW Pickup Info */}
        <div 
          className="p-4 rounded-xl"
          style={{
            background: 'linear-gradient(180deg, rgba(106,43,182,0.05), rgba(212,175,55,0.04))',
            border: '1px solid rgba(106,43,182,0.18)'
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-4 h-4 text-[#4a1776]" />
            <h3 className="text-sm font-semibold text-gray-800">Point de retrait EXW — {zoneCode}</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Adresse d'enlèvement :</p>
              <p className="font-medium text-gray-900">{replaceVariables(vars.POINT_EXW_ADRESSE || '[À définir]', vars)}</p>
            </div>
            <div>
              <p className="text-gray-500">Créneau proposé :</p>
              <p className="font-medium text-gray-900">{replaceVariables(vars.CRENEAU_EXW || '[À confirmer]', vars)}</p>
            </div>
          </div>
        </div>

        {/* Products Table with Barcode */}
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 55%, #4a1776 100%)' }}>
                <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Désignation</th>
                <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Lot/Palette</th>
                <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-right">Qté</th>
                <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-right">PU HT</th>
                <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-right">Total HT</th>
              </tr>
            </thead>
            <tbody>
              {products.length > 0 ? products.map((product, idx) => {
                const barcodeValue = product.barcode || generateBarcode(product.sku);
                return (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-purple-50/30' : ''}>
                    <td className="py-3 px-4">
                      <p className="font-semibold text-gray-900">{product.label}</p>
                      <p className="text-xs text-gray-500">SKU: {product.sku} {product.dlc ? `· DLC: ${product.dlc}` : ''}</p>
                      {/* Barcode */}
                      {barcodeValue && (
                        <div className="mt-2 flex flex-col items-start">
                          <Barcode 
                            value={barcodeValue}
                            format="EAN13"
                            width={1}
                            height={30}
                            fontSize={10}
                            margin={0}
                            displayValue={true}
                          />
                          <span className="text-[10px] text-gray-400 mt-0.5 font-mono">{barcodeValue}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-600">{product.lot || '-'}</td>
                    <td className="py-3 px-4 text-right text-gray-900">{product.qty}</td>
                    <td className="py-3 px-4 text-right text-gray-900">{formatCurrency(product.unit_price_ht * 100)}</td>
                    <td className="py-3 px-4 text-right font-semibold text-gray-900">{formatCurrency((product.total_ht || product.unit_price_ht * product.qty) * 100)}</td>
                  </tr>
                );
              }) : (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-gray-400 italic">
                    Aucun produit dans la commande
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr className="bg-gray-50 border-t-2 border-gray-200">
                <td colSpan={4} className="py-3 px-4 text-right font-semibold text-gray-700">Sous-total marchandises HT</td>
                <td className="py-3 px-4 text-right font-bold text-gray-900">{formatCurrency(productsSubtotalHT)}</td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* ===== PREPARATION OPTIONS - ZONE BASED ===== */}
        <div 
          className="p-6 rounded-2xl"
          style={{
            background: 'linear-gradient(180deg, rgba(16,185,129,0.05), rgba(212,175,55,0.03))',
            border: '2px solid rgba(16,185,129,0.2)'
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-emerald-600" />
              <h3 className="text-lg font-bold text-gray-900">
                Options de préparation — {zoneCode}
              </h3>
              {isVatExonerated && (
                <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                  TVA exonérée
                </Badge>
              )}
            </div>
            {calculating && (
              <RefreshCw className="w-4 h-4 text-emerald-600 animate-spin" />
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
              <span className="ml-2 text-gray-500">Chargement des options...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 py-4 text-red-600">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          ) : preparationOptions.length === 0 ? (
            <div className="flex items-center gap-2 py-4 text-gray-500">
              <Info className="w-5 h-5" />
              <span>Aucune option de préparation configurée pour cette zone.</span>
            </div>
          ) : (
            <div className="space-y-3">
              {preparationOptions.map((option) => {
                const isSelected = selectedOptions[option.id];
                const qty = quantities[option.id] || 1;
                const showQuantity = ['PER_UNIT', 'PALLET', 'CARTON', 'CONTAINER', 'PER_KG'].includes(option.pricing_mode);
                const optionExonerated = option.tva_exonerated || option.tva_rate === 0;
                
                return (
                  <div 
                    key={option.id}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      isSelected 
                        ? 'border-emerald-500 bg-emerald-50/50' 
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                    data-testid={`preparation-option-${option.id}`}
                  >
                    <div className="flex items-start gap-4">
                      <Checkbox
                        id={option.id}
                        checked={isSelected}
                        onCheckedChange={() => toggleOption(option.id, option.is_required)}
                        disabled={option.is_required}
                        className="mt-1"
                      />
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <label 
                            htmlFor={option.id}
                            className="font-semibold text-gray-900 cursor-pointer"
                          >
                            {option.name}
                          </label>
                          <Badge variant="outline" className={getTypeColor(option.preparation_type || option.code)}>
                            {option.code || option.preparation_type}
                          </Badge>
                          {option.is_required && (
                            <Badge variant="destructive" className="text-xs">Obligatoire</Badge>
                          )}
                          {option.is_default && !option.is_required && (
                            <Badge variant="secondary" className="text-xs">Recommandé</Badge>
                          )}
                          {optionExonerated && (
                            <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-600 border-emerald-200">
                              TVA 0%
                            </Badge>
                          )}
                        </div>
                        
                        {option.description && (
                          <p className="text-sm text-gray-500 mt-1">{option.description}</p>
                        )}
                        
                        <div className="flex items-center gap-4 mt-2">
                          <span className="text-sm font-medium text-emerald-700">
                            {formatCurrency(option.price_ht_cents)} HT
                            <span className="text-gray-500 font-normal ml-1">
                              {getPricingModeLabel(option.pricing_mode)}
                            </span>
                          </span>
                          <span className="text-xs text-gray-400">
                            {optionExonerated ? 'Exonéré TVA' : `TVA ${option.tva_rate}%`}
                          </span>
                          {option.sla_lead_time_hours > 0 && (
                            <span className="text-xs text-blue-600">
                              Délai: {option.sla_lead_time_hours}h
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Quantity selector */}
                      {showQuantity && isSelected && (
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => updateQuantity(option.id, -1)}
                            disabled={qty <= (option.min_qty || 1)}
                          >
                            <Minus className="h-3 w-3" />
                          </Button>
                          <span className="w-8 text-center font-mono font-bold">{qty}</span>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => updateQuantity(option.id, 1)}
                            disabled={qty >= (option.max_qty || 999999)}
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                      
                      {/* Calculated line total */}
                      {isSelected && calculatedTotals?.preparation_details && (
                        <div className="text-right min-w-[100px]">
                          {calculatedTotals.preparation_details
                            .filter(d => d.option_id === option.id)
                            .map(d => (
                              <span key={d.option_id} className="font-bold text-emerald-700">
                                {formatCurrency(d.total_ht_cents)} HT
                              </span>
                            ))
                          }
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ===== TOTALS SECTION ===== */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Récapitulatif</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Sous-total marchandises HT</span>
                <span className="font-mono">{formatCurrency(calculatedTotals?.products_subtotal_ht_cents || productsSubtotalHT)}</span>
              </div>
              
              {calculatedTotals?.preparation_subtotal_ht_cents > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Frais de préparation HT</span>
                  <span className="font-mono">{formatCurrency(calculatedTotals.preparation_subtotal_ht_cents)}</span>
                </div>
              )}
              
              <div className="flex justify-between font-bold pt-2 border-t border-gray-200">
                <span>Total HT</span>
                <span className="font-mono">{formatCurrency(calculatedTotals?.grand_total_ht_cents || productsSubtotalHT)}</span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">
                  TVA {isVatExonerated ? '(exonérée)' : `(${zoneTvaRate}% DOM)`}
                </span>
                <span className={`font-mono ${isVatExonerated ? 'text-emerald-600' : ''}`}>
                  {isVatExonerated ? '0,00 €' : formatCurrency(calculatedTotals?.grand_total_tva_cents || productsTVA)}
                </span>
              </div>
              
              <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                <span>Total TTC</span>
                <span className="font-mono text-[#4a1776]">
                  {formatCurrency(calculatedTotals?.grand_total_ttc_cents || (productsSubtotalHT + productsTVA))}
                </span>
              </div>
            </div>
          </div>
          
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Conditions</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• Incoterm : <strong className="text-gray-900">EXW</strong> (enlèvement à charge de l'acheteur)</p>
              <p>• Paiement : à réception de facture</p>
              <p>• Validité de l'offre : 30 jours</p>
              <p>• CGV KDMARCHE B2B applicables</p>
              {isVatExonerated && (
                <p className="text-emerald-600 font-medium">• Zone exonérée de TVA (article 294 CGI)</p>
              )}
            </div>
          </div>
        </div>

        {/* ===== SIGNATURE BLOCK WITH STAMP ===== */}
        <div 
          className="mt-8 p-6 rounded-2xl"
          style={{
            background: 'linear-gradient(180deg, rgba(26,11,46,0.02), rgba(212,175,55,0.03))',
            border: '2px solid rgba(26,11,46,0.12)'
          }}
        >
          <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#4a1776]" />
            Signatures
          </h3>
          
          <div className="grid md:grid-cols-2 gap-8">
            {/* Vendor Signature */}
            <div className="relative">
              <div className="p-4 rounded-xl bg-white border border-gray-200 min-h-[200px]">
                <p className="text-xs font-semibold uppercase tracking-wider text-[#b07a1a] mb-3">
                  Pour le Vendeur — KDMARCHE
                </p>
                <p className="text-sm text-gray-700 mb-1">{replaceVariables(vars.KDM_REP_NAME, vars)}</p>
                <p className="text-xs text-gray-500 mb-4">{replaceVariables(vars.KDM_REP_TITLE, vars)}</p>
                
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                  <Calendar className="w-3 h-3" />
                  <span>Date : {signatureData.signatureDate}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                  <MapPin className="w-3 h-3" />
                  <span>Lieu : {replaceVariables(vars.LIEU_SIGNATURE || 'Baie-Mahault', vars)}</span>
                </div>
                
                <div className="border-t border-dashed border-gray-300 pt-3 mt-4">
                  <p className="text-xs text-gray-400">Signature et cachet :</p>
                </div>
                
                {showStamp && (
                  <div className="absolute bottom-4 right-4 opacity-90">
                    <img 
                      src="/kdmarche-stamp.svg" 
                      alt="Tampon KDMARCHE PRO" 
                      className="w-24 h-24 transform rotate-[-8deg]"
                      style={{
                        filter: 'drop-shadow(2px 2px 4px rgba(198, 1, 1, 0.3))'
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
            
            {/* Client Signature */}
            <div className="p-4 rounded-xl bg-white border border-gray-200 min-h-[200px]">
              <p className="text-xs font-semibold uppercase tracking-wider text-[#4a1776] mb-3">
                Pour l'Acheteur
              </p>
              <p className="text-sm text-gray-700 mb-1">
                {signatureData.clientName || replaceVariables(vars.CLIENT_CONTACT || '[Nom du signataire]', vars)}
              </p>
              <p className="text-xs text-gray-500 mb-4">
                {signatureData.clientTitle || '[Qualité / Fonction]'}
              </p>
              
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <Calendar className="w-3 h-3" />
                <span>Date : ___/___/______</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                <MapPin className="w-3 h-3" />
                <span>Lieu : {signatureData.signatureLocation || '________________________'}</span>
              </div>
              
              <div className="border-t border-dashed border-gray-300 pt-3 mt-4">
                <p className="text-xs text-gray-400">Signature précédée de la mention "Bon pour accord" :</p>
              </div>
            </div>
          </div>
          
          <div className="mt-6 p-3 rounded-lg bg-[#d4af37]/5 border border-[#d4af37]/20">
            <p className="text-xs text-gray-600 text-center">
              <strong>Mention obligatoire :</strong> En signant ce bon de commande, l'acheteur reconnaît avoir pris connaissance 
              et accepté les CGV KDMARCHE B2B disponibles sur <span className="text-[#4a1776]">kdmarche-oscop.fr/legal/cgv-kdmarche</span>
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
        <div>
          <p><strong>KDMARCHE</strong> — Bon de commande B2B (EXW) — Zone {zoneCode} {isVatExonerated && '— TVA exonérée'}</p>
          <p className="mt-1">Flux marchandises uniquement. Services d'accès : facturation séparée par O'SCOP.</p>
        </div>
        <p className="font-mono">Réf. {replaceVariables(vars.COMMANDE_REF || 'BC-XXXX', vars)} · Page 1/1</p>
      </footer>
    </div>
  );
};

export default DynamicOrderForm;
