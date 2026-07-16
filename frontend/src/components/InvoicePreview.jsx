import i18n from '@/i18n';
import React from 'react';
import { replaceVariables, legalVariables, invoiceTemplate } from '../data/legalDocuments';
import { CheckCircle2, Truck, FileText, CreditCard, Building2 } from 'lucide-react';

// Invoice Preview Component - Dynamic generation before payment
// Can be embedded in checkout flow or order confirmation

const InvoicePreview = ({ 
  orderData = {},
  products = [],
  fees = [],
  totals = {},
  onDownload 
}) => {
  // Merge order data with default variables
  const vars = { ...legalVariables, ...orderData };
  
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat(i18n.language, { 
      style: 'currency', 
      currency: vars.DEVISE || 'EUR' 
    }).format(amount || 0);
  };

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-xl text-gray-900 print:shadow-none">
      {/* Premium Header - Purple & Gold Gradient */}
      <header 
        className="relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 45%, #4a1776 100%)',
          padding: '32px'
        }}
      >
        {/* Decorative overlay */}
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
            {/* Brand & Title */}
            <div className="flex items-center gap-4">
              <div 
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ 
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.16)'
                }}
              >
                <FileText className="w-8 h-8 text-[#d4af37]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">FACTURE</h1>
                <p className="text-white/70 text-sm mt-1">
                  Vente B2B de marchandises — <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-[#d4af37]/20 text-[#f2d07a] border border-[#d4af37]/40">EXW</span>
                </p>
              </div>
            </div>
            
            {/* Invoice Meta */}
            <div className="text-right text-white/80 text-sm space-y-1">
              <p>Facture n° <span className="font-mono text-white">{replaceVariables(vars.FACTURE_NUM, vars)}</span></p>
              <p>Date : <span className="font-mono text-white">{replaceVariables(vars.DATE_FACTURE, vars)}</span></p>
              <p>Échéance : <span className="font-mono text-white">{replaceVariables(vars.DATE_ECHEANCE, vars)}</span></p>
              <p>Devise : <span className="font-mono text-white">{vars.DEVISE}</span></p>
            </div>
          </div>
          
          {/* Tags */}
          <div className="flex flex-wrap gap-2 mt-4">
            {[
              { icon: CheckCircle2, label: 'B2B uniquement', color: '#d4af37' },
              { icon: Truck, label: 'Flux marchandises : KDMARCHE', color: '#d4af37' },
              { icon: CreditCard, label: 'Aucun abonnement / crédit O\'SCOP', color: '#fff' },
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
            <span 
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs text-white/90"
              style={{ 
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.14)'
              }}
            >
              Zone : <span className="font-mono">{vars.ZONE_CODE}</span>
            </span>
          </div>
        </div>
      </header>

      <main className="p-8 space-y-6">
        {/* Parties Grid */}
        <div className="grid md:grid-cols-2 gap-4">
          {/* Vendor */}
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-[#b07a1a]" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Vendeur</h3>
            </div>
            <p className="font-bold text-gray-900">{replaceVariables(vars.KDM_LEGAL_NAME, vars)}</p>
            <p className="text-sm text-gray-600 mt-1">
              {replaceVariables(vars.KDM_FORM, vars)} — {replaceVariables(vars.KDM_ADDRESS, vars)}
            </p>
            <p className="text-sm text-gray-600">SIRET : {replaceVariables(vars.KDM_SIRET, vars)} · TVA : {replaceVariables(vars.KDM_TVA, vars)}</p>
            <p className="text-sm text-gray-600">Email : {replaceVariables(vars.KDM_EMAIL, vars)} · Tél : {replaceVariables(vars.KDM_PHONE, vars)}</p>
          </div>
          
          {/* Client */}
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-[#4a1776]" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Acheteur (B2B)</h3>
            </div>
            <p className="font-bold text-gray-900">{replaceVariables(vars.CLIENT_LEGAL_NAME, vars)}</p>
            <p className="text-sm text-gray-600 mt-1">{replaceVariables(vars.CLIENT_ADDRESS, vars)}</p>
            <p className="text-sm text-gray-600">SIRET : {replaceVariables(vars.CLIENT_SIRET, vars)} · TVA : {replaceVariables(vars.CLIENT_TVA, vars)}</p>
            <p className="text-sm text-gray-600">Contact : {replaceVariables(vars.CLIENT_CONTACT, vars)}</p>
          </div>
        </div>

        {/* Order Reference */}
        <div 
          className="p-4 rounded-xl"
          style={{
            background: 'linear-gradient(180deg, rgba(106,43,182,0.05), rgba(212,175,55,0.04))',
            border: '1px solid rgba(106,43,182,0.18)'
          }}
        >
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <p><span className="font-semibold">Commande</span> : <span className="font-mono">{replaceVariables(vars.COMMANDE_REF, vars)}</span></p>
            <p><span className="font-semibold">Incoterm</span> : <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-[#d4af37]/20 text-[#b07a1a]">EXW</span></p>
            <p><span className="font-semibold">Point EXW</span> : <span className="font-mono text-gray-600">{replaceVariables(vars.POINT_EXW_ADRESSE, vars)}</span></p>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Créneau enlèvement : <span className="font-mono">{replaceVariables(vars.CRENEAU_EXW, vars)}</span> · 
            Référence enlèvement : <span className="font-mono">{replaceVariables(vars.PICKUP_REF, vars)}</span>
          </div>
        </div>

        {/* Products Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 55%, #4a1776 100%)' }}>
                {invoiceTemplate.productColumns.map((col, idx) => (
                  <th 
                    key={idx} 
                    className={`py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold ${idx >= 2 ? 'text-right' : 'text-left'}`}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {products.length > 0 ? products.map((product, idx) => (
                <tr key={idx} className={idx % 2 === 1 ? 'bg-purple-50/30' : ''}>
                  <td className="py-3 px-4">
                    <p className="font-semibold text-gray-900">{product.label}</p>
                    <p className="text-xs text-gray-500">SKU: {product.sku} · DLC/DDM: {product.dlc || 'N/A'}</p>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{product.lot}</td>
                  <td className="py-3 px-4 text-right text-gray-900">{product.qty}</td>
                  <td className="py-3 px-4 text-right text-gray-900">{formatCurrency(product.unit_price_ht)}</td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-900">{formatCurrency(product.total_ht)}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-gray-400 italic">
                    Aucun produit ajouté
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Fees Table */}
        {fees.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 55%, #4a1776 100%)' }}>
                  <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Frais accessoires (B2B)</th>
                  <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Base</th>
                  <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-right">Montant HT</th>
                </tr>
              </thead>
              <tbody>
                {fees.map((fee, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-purple-50/30' : ''}>
                    <td className="py-3 px-4 font-semibold text-gray-900">{fee.label}</td>
                    <td className="py-3 px-4 text-gray-500">{fee.description}</td>
                    <td className="py-3 px-4 text-right font-semibold text-gray-900">{formatCurrency(fee.amount_ht)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Compliance Note */}
        <div 
          className="p-4 rounded-xl text-sm"
          style={{
            background: 'linear-gradient(180deg, rgba(212,175,55,0.08), rgba(106,43,182,0.05))',
            border: '1px solid rgba(212,175,55,0.30)'
          }}
        >
          <p className="font-semibold text-gray-800 mb-1">Information conformité :</p>
          <p className="text-gray-600">{invoiceTemplate.compliance_note}</p>
        </div>

        {/* Totals */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Récapitulatif HT</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Sous-total marchandises HT</span>
                <span className="font-mono">{formatCurrency(totals.subtotal_products_ht || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Sous-total frais accessoires HT</span>
                <span className="font-mono">{formatCurrency(totals.subtotal_fees_ht || 0)}</span>
              </div>
              <div className="flex justify-between font-bold pt-2 border-t border-gray-200">
                <span>Total HT</span>
                <span className="font-mono">{formatCurrency(totals.total_ht || 0)}</span>
              </div>
            </div>
          </div>
          
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Taxes & Total</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">TVA ({vars.TVA_TAUX || 20}%)</span>
                <span className="font-mono">{formatCurrency(totals.tva_amount || 0)}</span>
              </div>
              <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                <span>Total TTC</span>
                <span className="font-mono text-[#4a1776]">{formatCurrency(totals.total_ttc || 0)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Payment Info */}
        <div 
          className="p-4 rounded-xl"
          style={{
            background: 'linear-gradient(180deg, rgba(26,11,46,0.03), rgba(212,175,55,0.03))',
            border: '1px solid rgba(26,11,46,0.14)'
          }}
        >
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Modalités de paiement</h4>
          <div className="text-sm text-gray-700 space-y-1">
            <p>Moyen : {vars.MOYEN_PAIEMENT || 'Virement bancaire'} · Référence : <span className="font-mono">{vars.PAIEMENT_REF || 'À définir'}</span></p>
            <p>IBAN : <span className="font-mono">{replaceVariables(vars.IBAN, vars)}</span> · BIC : <span className="font-mono">{replaceVariables(vars.BIC, vars)}</span></p>
            <p className="text-xs text-gray-500 mt-2">Pénalités de retard (B2B) : taux légal + indemnité forfaitaire 40 €.</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
        <p>{invoiceTemplate.footer_note}</p>
        <p className="font-mono">Facture {replaceVariables(vars.FACTURE_NUM, vars)} · Page 1/1</p>
      </footer>
    </div>
  );
};

export default InvoicePreview;
