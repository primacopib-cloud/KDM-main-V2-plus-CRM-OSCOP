import React from 'react';
import { replaceVariables, legalVariables, invoiceTemplate } from '../data/legalDocuments';
import { CheckCircle2, Truck, FileText, Building2, Calendar, Hash, MapPin, Package } from 'lucide-react';

// Order Form / Bon de Commande Component with Signature Block and Stamp
// Used for order confirmation before payment

const OrderFormPreview = ({ 
  orderData = {},
  products = [],
  fees = [],
  totals = {},
  signatureData = {
    clientName: '',
    clientTitle: '',
    signatureDate: new Date().toLocaleDateString('fr-FR'),
    signatureLocation: ''
  },
  showStamp = true,
  onDownload 
}) => {
  // Merge order data with default variables
  const vars = { ...legalVariables, ...orderData };
  
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', { 
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
                <Package className="w-8 h-8 text-[#d4af37]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">BON DE COMMANDE</h1>
                <p className="text-white/70 text-sm mt-1">
                  Vente B2B de marchandises — <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-[#d4af37]/20 text-[#f2d07a] border border-[#d4af37]/40">EXW</span>
                </p>
              </div>
            </div>
            
            {/* Order Meta */}
            <div className="text-right text-white/80 text-sm space-y-1">
              <p>Commande n° <span className="font-mono text-white">{replaceVariables(vars.COMMANDE_REF || 'BC-XXXX-XXXX', vars)}</span></p>
              <p>Date : <span className="font-mono text-white">{replaceVariables(vars.DATE_FACTURE || new Date().toLocaleDateString('fr-FR'), vars)}</span></p>
              <p>Zone : <span className="font-mono text-white">{vars.ZONE_CODE || 'N/A'}</span></p>
            </div>
          </div>
          
          {/* Tags */}
          <div className="flex flex-wrap gap-2 mt-4">
            {[
              { icon: CheckCircle2, label: 'B2B uniquement', color: '#d4af37' },
              { icon: Truck, label: 'Incoterm EXW', color: '#d4af37' },
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
            <p className="text-sm text-gray-600">SIRET : {replaceVariables(vars.KDM_SIRET, vars)}</p>
            <p className="text-sm text-gray-600">TVA : {replaceVariables(vars.KDM_TVA, vars)}</p>
          </div>
          
          {/* Client */}
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
            <h3 className="text-sm font-semibold text-gray-800">Point de retrait EXW</h3>
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

        {/* Products Table */}
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
              {products.length > 0 ? products.map((product, idx) => (
                <tr key={idx} className={idx % 2 === 1 ? 'bg-purple-50/30' : ''}>
                  <td className="py-3 px-4">
                    <p className="font-semibold text-gray-900">{product.label}</p>
                    <p className="text-xs text-gray-500">SKU: {product.sku} {product.dlc ? `· DLC: ${product.dlc}` : ''}</p>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{product.lot || '-'}</td>
                  <td className="py-3 px-4 text-right text-gray-900">{product.qty}</td>
                  <td className="py-3 px-4 text-right text-gray-900">{formatCurrency(product.unit_price_ht)}</td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-900">{formatCurrency(product.total_ht)}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-gray-400 italic">
                    Aucun produit dans la commande
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Fees if any */}
        {fees.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'linear-gradient(135deg, #1a0b2e 0%, #341057 55%, #4a1776 100%)' }}>
                  <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Frais accessoires</th>
                  <th className="py-3 px-4 text-white text-xs uppercase tracking-wider font-semibold text-left">Description</th>
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

        {/* Totals */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Récapitulatif</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Sous-total marchandises HT</span>
                <span className="font-mono">{formatCurrency(totals.subtotal_products_ht || 0)}</span>
              </div>
              {totals.subtotal_fees_ht > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Frais accessoires HT</span>
                  <span className="font-mono">{formatCurrency(totals.subtotal_fees_ht)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold pt-2 border-t border-gray-200">
                <span>Total HT</span>
                <span className="font-mono">{formatCurrency(totals.total_ht || 0)}</span>
              </div>
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
          
          {/* Terms */}
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Conditions</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• Incoterm : <strong className="text-gray-900">EXW</strong> (enlèvement à charge de l'acheteur)</p>
              <p>• Paiement : à réception de facture</p>
              <p>• Validité de l'offre : 30 jours</p>
              <p>• CGV KDMARCHE B2B applicables</p>
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
            {/* Vendor Signature - KDMARCHE with STAMP */}
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
                
                {/* Signature line */}
                <div className="border-t border-dashed border-gray-300 pt-3 mt-4">
                  <p className="text-xs text-gray-400">Signature et cachet :</p>
                </div>
                
                {/* KDMARCHE STAMP - Positioned in signature area */}
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
              
              {/* Signature line */}
              <div className="border-t border-dashed border-gray-300 pt-3 mt-4">
                <p className="text-xs text-gray-400">Signature précédée de la mention "Bon pour accord" :</p>
              </div>
            </div>
          </div>
          
          {/* Legal mention */}
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
          <p><strong>KDMARCHE</strong> — Bon de commande B2B (EXW)</p>
          <p className="mt-1">Flux marchandises uniquement. Services d'accès : facturation séparée par O'SCOP.</p>
        </div>
        <p className="font-mono">Réf. {replaceVariables(vars.COMMANDE_REF || 'BC-XXXX', vars)} · Page 1/1</p>
      </footer>
    </div>
  );
};

export default OrderFormPreview;
