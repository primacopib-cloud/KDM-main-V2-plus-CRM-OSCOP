import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileText, Download, Printer } from 'lucide-react';
import { Button } from '../components/ui/button';
import { partners } from '../data/mock';
import OrderFormPreview from '../components/OrderFormPreview';

// Demo page to preview Order Form with Stamp
export default function OrderPreviewPage() {
  // Sample order data for demonstration
  const sampleOrderData = {
    COMMANDE_REF: 'BC-2026-00147',
    DATE_FACTURE: '17/01/2026',
    ZONE_CODE: 'GP-971',
    CLIENT_LEGAL_NAME: 'SARL DISTRIBUTION CARAÏBES',
    CLIENT_ADDRESS: '15 Avenue des Palmiers, 97100 Basse-Terre, Guadeloupe',
    CLIENT_SIRET: '812 345 678 00012',
    CLIENT_TVA: 'FR 82 812345678',
    CLIENT_CONTACT: 'Jean-Pierre MARTIN',
    POINT_EXW_ADRESSE: 'Entrepôt KDMARCHE - ZI Jarry, 97122 Baie-Mahault',
    CRENEAU_EXW: 'Lundi 20/01/2026, 8h-12h',
    LIEU_SIGNATURE: 'Baie-Mahault',
  };

  const sampleProducts = [
    { 
      label: 'Riz Basmati Premium 5kg',
      sku: 'ALI-RIZ-001',
      lot: 'Palette x48',
      dlc: '15/06/2027',
      qty: 2,
      unit_price_ht: 245.00,
      total_ht: 490.00
    },
    { 
      label: 'Huile de Tournesol 5L',
      sku: 'ALI-HUI-003',
      lot: 'Carton x6',
      dlc: '20/12/2026',
      qty: 10,
      unit_price_ht: 42.50,
      total_ht: 425.00
    },
    { 
      label: 'Sucre de Canne Roux 25kg',
      sku: 'EPI-SUC-002',
      lot: 'Palette x40',
      qty: 1,
      unit_price_ht: 580.00,
      total_ht: 580.00
    },
    { 
      label: 'Lait UHT Demi-écrémé 1L',
      sku: 'FRA-LAI-001',
      lot: 'Palette x720',
      dlc: '01/04/2026',
      qty: 1,
      unit_price_ht: 720.00,
      total_ht: 720.00
    },
  ];

  const sampleFees = [
    { 
      label: 'Frais de préparation commande',
      description: 'Pick & pack / palettisation',
      amount_ht: 45.00
    }
  ];

  const subtotalProducts = sampleProducts.reduce((sum, p) => sum + p.total_ht, 0);
  const subtotalFees = sampleFees.reduce((sum, f) => sum + f.amount_ht, 0);
  const totalHT = subtotalProducts + subtotalFees;
  const tvaAmount = totalHT * 0.20;
  const totalTTC = totalHT + tvaAmount;

  const sampleTotals = {
    subtotal_products_ht: subtotalProducts,
    subtotal_fees_ht: subtotalFees,
    total_ht: totalHT,
    tva_amount: tvaAmount,
    total_ttc: totalTTC
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div 
      className="min-h-screen text-white"
      style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}
    >
      {/* Header */}
      <header 
        className="sticky top-0 z-50 print:hidden"
        style={{
          background: 'rgba(30,12,52,0.94)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1200px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/commandes" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Retour aux commandes</span>
            </Link>
            <div className="flex items-center gap-2">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-8 w-auto object-contain" />
              <span className="text-white/30 text-xs">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm"
              className="text-xs border-white/10 hover:bg-white/5"
              onClick={handlePrint}
            >
              <Printer className="w-3.5 h-3.5 mr-1.5" />
              Imprimer
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              className="text-xs border-[#d4af37]/30 text-[#d4af37] hover:bg-[#d4af37]/10"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Télécharger PDF
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-[1000px] mx-auto px-5 py-8">
        {/* Page Title */}
        <div className="mb-8 text-center print:hidden">
          <h1 className="text-2xl font-bold mb-2 flex items-center justify-center gap-3">
            <FileText className="w-6 h-6 text-[#d4af37]" />
            Bon de Commande
          </h1>
          <p className="text-white/60 text-sm">
            Aperçu avec tampon KDMARCHE PRO intégré
          </p>
        </div>

        {/* Order Form Preview with Stamp */}
        <OrderFormPreview 
          orderData={sampleOrderData}
          products={sampleProducts}
          fees={sampleFees}
          totals={sampleTotals}
          signatureData={{
            clientName: 'Jean-Pierre MARTIN',
            clientTitle: 'Gérant',
            signatureDate: '17/01/2026',
            signatureLocation: 'Basse-Terre'
          }}
          showStamp={true}
        />

        {/* Info Note */}
        <div className="mt-8 p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] text-center print:hidden">
          <p className="text-xs text-white/50">
            Ce document peut être imprimé ou téléchargé en PDF. Le tampon KDMARCHE PRO 
            est automatiquement apposé dans le bloc de signature du vendeur.
          </p>
        </div>
      </div>
    </div>
  );
}
