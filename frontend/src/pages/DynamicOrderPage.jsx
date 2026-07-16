import i18n from '@/i18n';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DynamicOrderForm from '../components/DynamicOrderForm';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { ArrowLeft, FileText, Download, Send, Plus, Package, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

// Page de démonstration du Bon de Commande Dynamique avec options de préparation par zone
const DynamicOrderPage = () => {
  const navigate = useNavigate();
  const [selectedZone, setSelectedZone] = useState('GUADELOUPE');
  const [calculatedTotals, setCalculatedTotals] = useState(null);
  const [preparationDetails, setPreparationDetails] = useState([]);

  // Demo products
  const [products] = useState([
    { 
      label: 'Riz long grain 5kg', 
      sku: 'ALI-RIZ-001', 
      lot: 'LOT-2026-A12', 
      qty: 10, 
      unit_price_ht: 12.50,
      dlc: '2026-12-31'
    },
    { 
      label: 'Huile de tournesol 5L', 
      sku: 'ALI-HUI-001', 
      lot: 'LOT-2026-B08', 
      qty: 24, 
      unit_price_ht: 8.90 
    },
    { 
      label: 'Eau minérale 1.5L (pack 6)', 
      sku: 'BOI-EAU-001', 
      lot: 'PAL-2026-C03', 
      qty: 100, 
      unit_price_ht: 3.20 
    },
    { 
      label: 'Savon liquide 5L', 
      sku: 'HYG-SAV-001', 
      lot: 'LOT-2026-D15', 
      qty: 12, 
      unit_price_ht: 7.80 
    },
  ]);

  const zones = [
    { code: 'GUADELOUPE', name: 'Guadeloupe (971)' },
    { code: 'MARTINIQUE', name: 'Martinique (972)' },
    { code: 'GUYANE', name: 'Guyane (973)' },
    { code: 'REUNION', name: 'La Réunion (974)' },
  ];

  const handleTotalsChange = (totals) => {
    setCalculatedTotals(totals);
    console.log('Totals updated:', totals);
  };

  const handlePreparationChange = (details) => {
    setPreparationDetails(details);
    console.log('Preparation details:', details);
  };

  const handleSubmitOrder = () => {
    if (!calculatedTotals) {
      toast.error('Veuillez attendre le calcul des totaux');
      return;
    }
    
    toast.success('Bon de commande validé !', {
      description: `Total TTC: ${(calculatedTotals.grand_total_ttc_cents / 100).toFixed(2)}€ — Zone: ${selectedZone}`
    });
  };

  const formatCurrency = (cents) => {
    return new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR' }).format(cents / 100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate(-1)}
                className="hover:bg-gray-100"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-purple-600" />
                  Bon de Commande Dynamique
                </h1>
                <p className="text-sm text-gray-500">Options de préparation conditionnelles par zone</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Select value={selectedZone} onValueChange={setSelectedZone}>
                <SelectTrigger className="w-[200px]" data-testid="zone-selector">
                  <SelectValue placeholder="Sélectionner une zone" />
                </SelectTrigger>
                <SelectContent>
                  {zones.map(zone => (
                    <SelectItem key={zone.code} value={zone.code}>
                      {zone.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Button variant="outline" className="gap-2">
                <Download className="w-4 h-4" />
                PDF
              </Button>
              
              <Button 
                className="gap-2 bg-purple-600 hover:bg-purple-700"
                onClick={handleSubmitOrder}
                data-testid="submit-order-btn"
              >
                <Send className="w-4 h-4" />
                Valider la commande
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Order Form - 2 columns */}
          <div className="lg:col-span-2">
            <DynamicOrderForm
              zoneCode={selectedZone}
              products={products}
              orderData={{
                COMMANDE_REF: 'BC-2026-DEMO-001',
                DATE_FACTURE: new Date().toLocaleDateString(i18n.language),
                CLIENT_LEGAL_NAME: 'SOCIÉTÉ DÉMONSTRATION SARL',
                CLIENT_ADDRESS: '123 Rue de la Démo, 97100 Basse-Terre',
                CLIENT_SIRET: '123 456 789 00012',
                CLIENT_CONTACT: 'Jean Martin',
                POINT_EXW_ADRESSE: 'Zone Industrielle de Jarry, 97122 Baie-Mahault',
                CRENEAU_EXW: 'Lun-Ven 8h-12h / 14h-17h'
              }}
              signatureData={{
                clientName: 'Jean Martin',
                clientTitle: 'Directeur des Achats',
                signatureDate: new Date().toLocaleDateString(i18n.language),
                signatureLocation: ''
              }}
              onTotalsChange={handleTotalsChange}
              onPreparationChange={handlePreparationChange}
            />
          </div>
          
          {/* Side Panel - Summary */}
          <div className="lg:col-span-1 space-y-6">
            {/* Zone Info Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Package className="w-5 h-5 text-purple-600" />
                  Zone sélectionnée
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="p-4 rounded-xl bg-purple-50 border border-purple-200">
                  <p className="text-2xl font-bold text-purple-700">{selectedZone}</p>
                  <p className="text-sm text-purple-600 mt-1">
                    {zones.find(z => z.code === selectedZone)?.name}
                  </p>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Les options de préparation et les tarifs varient selon la zone géographique sélectionnée.
                </p>
              </CardContent>
            </Card>

            {/* Calculation Summary Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-emerald-600" />
                  Calcul serveur
                </CardTitle>
                <CardDescription>
                  Totaux calculés et validés côté serveur
                </CardDescription>
              </CardHeader>
              <CardContent>
                {calculatedTotals ? (
                  <div className="space-y-4">
                    <div className="p-3 rounded-lg bg-gray-50 space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Marchandises HT</span>
                        <span className="font-mono">{formatCurrency(calculatedTotals.products_subtotal_ht_cents)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">TVA marchandises</span>
                        <span className="font-mono">{formatCurrency(calculatedTotals.products_tva_cents)}</span>
                      </div>
                    </div>

                    {calculatedTotals.preparation_subtotal_ht_cents > 0 && (
                      <div className="p-3 rounded-lg bg-emerald-50 space-y-2 text-sm">
                        <p className="text-xs font-semibold text-emerald-700 uppercase">Préparation</p>
                        {calculatedTotals.preparation_details?.map((detail, idx) => (
                          <div key={idx} className="flex justify-between text-emerald-800">
                            <span className="truncate max-w-[150px]">{detail.option_name}</span>
                            <span className="font-mono">{formatCurrency(detail.total_ht_cents)}</span>
                          </div>
                        ))}
                        <div className="flex justify-between pt-2 border-t border-emerald-200">
                          <span className="font-semibold">Total préparation HT</span>
                          <span className="font-mono font-bold">{formatCurrency(calculatedTotals.preparation_subtotal_ht_cents)}</span>
                        </div>
                        <div className="flex justify-between text-emerald-600">
                          <span>TVA préparation</span>
                          <span className="font-mono">{formatCurrency(calculatedTotals.preparation_tva_cents)}</span>
                        </div>
                      </div>
                    )}

                    <div className="p-4 rounded-xl bg-purple-100 border-2 border-purple-300">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-purple-700">Total HT</span>
                        <span className="font-mono font-bold text-purple-800">{formatCurrency(calculatedTotals.grand_total_ht_cents)}</span>
                      </div>
                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-purple-700">TVA totale</span>
                        <span className="font-mono text-purple-800">{formatCurrency(calculatedTotals.grand_total_tva_cents)}</span>
                      </div>
                      <div className="flex justify-between pt-3 border-t border-purple-300">
                        <span className="text-lg font-bold text-purple-900">Total TTC</span>
                        <span className="text-2xl font-mono font-bold text-purple-900">
                          {formatCurrency(calculatedTotals.grand_total_ttc_cents)}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-gray-400 text-center">
                      Calcul à {new Date(calculatedTotals.calculation_timestamp).toLocaleTimeString(i18n.language)}
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                    <RefreshCw className="w-8 h-8 animate-spin mb-2" />
                    <p className="text-sm">Calcul en cours...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Help Card */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Comment ça fonctionne ?</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-gray-600 space-y-2">
                <p><strong>1.</strong> Sélectionnez une zone géographique</p>
                <p><strong>2.</strong> Les options de préparation disponibles s'affichent automatiquement</p>
                <p><strong>3.</strong> Cochez les options souhaitées (certaines sont obligatoires)</p>
                <p><strong>4.</strong> Le total est recalculé en temps réel côté serveur</p>
                <p><strong>5.</strong> Validez votre bon de commande</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default DynamicOrderPage;
