import i18n from '@/i18n';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileSignature, Phone, CheckCircle2, Shield, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { partners } from '../data/mock';

const SAMPLE_FEES = [{ label: 'Frais de préparation', description: 'Pick & pack', amount_ht: 45 }];
import SMSSignatureModal from '../components/SMSSignatureModal';
import OrderFormPreview from '../components/OrderFormPreview';
import { toast } from 'sonner';

export default function SignatureDemoPage() {
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [signatureResult, setSignatureResult] = useState(null);
  
  // Form state for signer info
  const [signerInfo, setSignerInfo] = useState({
    first_name: 'Jean-Pierre',
    last_name: 'MARTIN',
    email: 'jp.martin@test.com',
    phone: '+33612345678',
    company: 'SARL Distribution Caraïbes',
    title: 'Gérant'
  });
  
  // Sample order data
  const orderData = {
    COMMANDE_REF: 'BC-2026-00147',
    DATE_FACTURE: '17/01/2026',
    ZONE_CODE: 'GP-971',
    CLIENT_LEGAL_NAME: signerInfo.company,
    CLIENT_ADDRESS: '15 Avenue des Palmiers, 97100 Basse-Terre, Guadeloupe',
    CLIENT_SIRET: '812 345 678 00012',
    CLIENT_TVA: 'FR 82 812345678',
    CLIENT_CONTACT: `${signerInfo.first_name} ${signerInfo.last_name}`,
    POINT_EXW_ADRESSE: 'Entrepôt KDMARCHE - ZI Jarry, 97122 Baie-Mahault',
    CRENEAU_EXW: 'Lundi 20/01/2026, 8h-12h',
  };

  const sampleProducts = [
    { label: 'Riz Basmati Premium 5kg', sku: 'ALI-RIZ-001', lot: 'Palette x48', dlc: '15/06/2027', qty: 2, unit_price_ht: 245.00, total_ht: 490.00 },
    { label: 'Huile de Tournesol 5L', sku: 'ALI-HUI-003', lot: 'Carton x6', dlc: '20/12/2026', qty: 10, unit_price_ht: 42.50, total_ht: 425.00 },
  ];

  const totals = {
    subtotal_products_ht: 915.00,
    subtotal_fees_ht: 45.00,
    total_ht: 960.00,
    tva_amount: 192.00,
    total_ttc: 1152.00
  };
  
  const handleSignatureComplete = (result) => {
    setSignatureResult(result);
    setShowSignatureModal(false);
    toast.success('Document signé avec succès !');
  };
  
  const handleSignatureDeclined = () => {
    toast.info('Signature refusée');
    setShowSignatureModal(false);
  };

  return (
    <div 
      className="min-h-screen text-white"
      style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}
    >
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(30,12,52,0.94)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1200px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Retour</span>
            </Link>
            <div className="flex items-center gap-2">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-8 w-auto object-contain" />
              <span className="text-white/30 text-xs">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-[#4a1776]" />
            <span className="text-sm text-white/70">Signature SMS</span>
          </div>
        </div>
      </header>

      <div className="max-w-[1200px] mx-auto px-5 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Configuration */}
          <div className="space-y-6">
            <div className="text-center lg:text-left">
              <h1 className="text-2xl font-bold mb-2 flex items-center gap-3 justify-center lg:justify-start">
                <FileSignature className="w-6 h-6 text-[#d4af37]" />
                Signature par SMS (OTP)
              </h1>
              <p className="text-white/60 text-sm">
                Démonstration du workflow de signature électronique conforme eIDAS
              </p>
            </div>

            {/* Signer Info Form */}
            <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08]">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Phone className="w-5 h-5 text-[#4a1776]" />
                Informations du signataire
              </h2>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-white/70">Prénom</Label>
                  <Input 
                    value={signerInfo.first_name}
                    onChange={e => setSignerInfo({...signerInfo, first_name: e.target.value})}
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
                <div>
                  <Label className="text-white/70">Nom</Label>
                  <Input 
                    value={signerInfo.last_name}
                    onChange={e => setSignerInfo({...signerInfo, last_name: e.target.value})}
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-white/70">Email</Label>
                  <Input 
                    type="email"
                    value={signerInfo.email}
                    onChange={e => setSignerInfo({...signerInfo, email: e.target.value})}
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-white/70">Téléphone (format international)</Label>
                  <Input 
                    value={signerInfo.phone}
                    onChange={e => setSignerInfo({...signerInfo, phone: e.target.value})}
                    placeholder="+33612345678"
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-white/70">Société</Label>
                  <Input 
                    value={signerInfo.company}
                    onChange={e => setSignerInfo({...signerInfo, company: e.target.value})}
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-white/70">Fonction</Label>
                  <Input 
                    value={signerInfo.title}
                    onChange={e => setSignerInfo({...signerInfo, title: e.target.value})}
                    className="bg-white/5 border-white/10 text-white"
                  />
                </div>
              </div>
            </div>

            {/* Security Info */}
            <div className="p-4 rounded-xl bg-[#4a1776]/10 border border-[#4a1776]/20">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-[#4a1776] flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-white/90 mb-1">Signature conforme eIDAS</h3>
                  <ul className="text-sm text-white/60 space-y-1">
                    <li>• Niveau AES (Advanced Electronic Signature)</li>
                    <li>• Authentification par SMS OTP à 6 chiffres</li>
                    <li>• Code valable 10 minutes, 3 tentatives max</li>
                    <li>• Audit trail complet avec horodatage</li>
                    <li>• Hash SHA-256 pour preuve de signature</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Action Button */}
            <Button
              onClick={() => setShowSignatureModal(true)}
              className="w-full bg-[#4a1776] hover:bg-[#3a0d5e] h-12 text-base"
              data-testid="open-signature-modal-btn"
            >
              <FileSignature className="w-5 h-5 mr-2" />
              Lancer la signature SMS
            </Button>

            {/* Signature Result */}
            {signatureResult && (
              <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <span className="font-semibold text-green-400">Document signé</span>
                </div>
                <div className="space-y-2 text-sm">
                  <p className="text-white/70">
                    <span className="text-white/50">ID:</span> {signatureResult.signature_id}
                  </p>
                  <p className="text-white/70">
                    <span className="text-white/50">Hash:</span> 
                    <span className="font-mono text-xs">{signatureResult.signature_hash?.slice(0, 32)}...</span>
                  </p>
                  <p className="text-white/70">
                    <span className="text-white/50">Date:</span> {new Date(signatureResult.signed_at).toLocaleString(i18n.language)}
                  </p>
                </div>
              </div>
            )}

            {/* Note for testing */}
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-200/80">
                  <p className="font-semibold mb-1">Mode démonstration</p>
                  <p>Le code SMS est affiché dans les logs du serveur pour les tests. 
                  En production, il sera envoyé via Twilio ou un autre provider SMS.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Document Preview */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white/90">Aperçu du document</h2>
            <div className="rounded-2xl overflow-hidden shadow-2xl transform scale-[0.85] origin-top">
              <OrderFormPreview 
                orderData={orderData}
                products={sampleProducts}
                fees={SAMPLE_FEES}
                totals={totals}
                signatureData={{
                  clientName: `${signerInfo.first_name} ${signerInfo.last_name}`,
                  clientTitle: signerInfo.title,
                  signatureDate: new Date().toLocaleDateString(i18n.language),
                  signatureLocation: 'Guadeloupe'
                }}
                showStamp={true}
              />
            </div>
          </div>
        </div>
      </div>

      {/* SMS Signature Modal */}
      <SMSSignatureModal
        isOpen={showSignatureModal}
        onClose={() => setShowSignatureModal(false)}
        documentType="BON_COMMANDE"
        documentRef="BC-2026-00147"
        documentTitle="Bon de commande KDMARCHE B2B"
        signerInfo={signerInfo}
        documentPreview="Commande de marchandises B2B - Incoterm EXW - Total TTC: 1 152,00 €"
        onSignatureComplete={handleSignatureComplete}
        onSignatureDeclined={handleSignatureDeclined}
      />
    </div>
  );
}
