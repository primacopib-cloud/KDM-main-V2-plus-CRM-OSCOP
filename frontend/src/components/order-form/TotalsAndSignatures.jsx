import React from 'react';
import { 
  Package, Truck, FileText, Building2, Calendar, MapPin, 
  CheckCircle2, AlertCircle, Plus, Minus, RefreshCw, Info
} from 'lucide-react';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import { replaceVariables } from '../../data/legalDocuments';

export const TotalsAndSignatures = ({
  calculatedTotals, formatCurrency, productsSubtotalHT, productsTVA, zoneTvaRate,
  isVatExonerated, signatureData, showStamp, vars,
}) => (
  <>
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
              <p>• Incoterm : <strong className="text-gray-900">EXW</strong> (enlèvement à charge de l&apos;acheteur)</p>
              <p>• Paiement : à réception de facture</p>
              <p>• Validité de l&apos;offre : 30 jours</p>
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
                Pour l&apos;Acheteur
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
                <p className="text-xs text-gray-400">Signature précédée de la mention &quot;Bon pour accord&quot; :</p>
              </div>
            </div>
          </div>
          
          <div className="mt-6 p-3 rounded-lg bg-[#d4af37]/5 border border-[#d4af37]/20">
            <p className="text-xs text-gray-600 text-center">
              <strong>Mention obligatoire :</strong> En signant ce bon de commande, l&apos;acheteur reconnaît avoir pris connaissance 
              et accepté les CGV KDMARCHE B2B disponibles sur <span className="text-[#4a1776]">kdmarche-oscop.fr/legal/cgv-kdmarche</span>
            </p>
          </div>
        </div>

  </>
);
