import React from 'react';
import { 
  Package, Truck, FileText, Building2, Calendar, MapPin, 
  CheckCircle2, AlertCircle, Plus, Minus, RefreshCw, Info
} from 'lucide-react';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { replaceVariables } from '../../data/legalDocuments';

export const PreparationOptionsSection = ({
  preparationOptions, selectedOptions, quantities, loading, error, calculating,
  calculatedTotals, toggleOption, updateQuantity, getPricingModeLabel,
  getTypeColor, formatCurrency, zoneCode,
}) => (
  <>
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

  </>
);
