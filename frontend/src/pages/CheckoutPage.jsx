import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Package, MapPin, CreditCard, FileText, CheckCircle2, ArrowLeft,
  Truck, Calendar, Building2, RefreshCw, Shield, FileSignature, ChevronRight,
  Download, Loader2, Lock, AlertCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { toast } from 'sonner';

import DynamicOrderForm from '../components/DynamicOrderForm';
import SMSSignatureModal from '../components/SMSSignatureModal';
import DeliveryOptionsSelector from '../components/DeliveryOptionsSelector';
import { BreadcrumbPill } from '../components/Breadcrumb';
import { partners } from '../data/mock';
import { authAPI, catalogAPI, ordersAPIV2, zonesAPIV2 } from '../services/api';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Format currency
const formatCurrency = (cents) => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

// Steps configuration
const STEPS = [
  { id: 'review', label: 'Récapitulatif', icon: Package },
  { id: 'delivery', label: 'Livraison', icon: Truck },
  { id: 'preparation', label: 'Préparation', icon: Package },
  { id: 'signature', label: 'Signature', icon: FileSignature },
  { id: 'payment', label: 'Paiement', icon: CreditCard },
];

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const cartId = searchParams.get('cart');
  
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Zone & Options
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState('971');
  const [pickupLocations, setPickupLocations] = useState([]);
  const [selectedPickup, setSelectedPickup] = useState('');
  
  // Delivery options (LOGI'SCOP)
  const [deliveryOption, setDeliveryOption] = useState(null);
  
  // Preparation options
  const [preparationTotals, setPreparationTotals] = useState(null);
  const [preparationDetails, setPreparationDetails] = useState([]);
  
  // Order notes
  const [orderNotes, setOrderNotes] = useState('');
  
  // Installment
  const [useInstallment, setUseInstallment] = useState(false);
  const MIN_INSTALLMENT_CENTS = 550000;
  
  // Signature
  const [signatureModalOpen, setSignatureModalOpen] = useState(false);
  const [signatureComplete, setSignatureComplete] = useState(false);
  const [signatureData, setSignatureData] = useState(null);
  
  // Transport contract acceptance (LOGI'SCOP)
  const [transportContractAccepted, setTransportContractAccepted] = useState(false);
  
  // Final order
  const [submitting, setSubmitting] = useState(false);
  const [orderCreated, setOrderCreated] = useState(null);
  
  // Payment
  const [paymentMethod, setPaymentMethod] = useState('card'); // card, sepa
  const [processingPayment, setProcessingPayment] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [stripeSessionUrl, setStripeSessionUrl] = useState(null);

  // Build products from cart for DynamicOrderForm
  const products = cart?.items?.map(item => ({
    label: item.product_name,
    sku: item.product_sku,
    lot: '-',
    qty: item.quantity,
    unit_price_ht: item.price_ht_cents / 100,
    total_ht: item.line_total_ht_cents / 100,
    dlc: null
  })) || [];

  // Load data
  useEffect(() => {
    const init = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion?redirect=/checkout');
        return;
      }

      try {
        const userData = await authAPI.getMe();
        setUser(userData);

        // Load zones
        const zonesData = await zonesAPIV2.list();
        setZones(zonesData);
        
        if (zonesData.length > 0) {
          setSelectedZone(zonesData[0].code || 'GUADELOUPE');
        }

        // Load cart
        const cartData = await catalogAPI.getCart();
        if (!cartData || !cartData.items || cartData.items.length === 0) {
          toast.error('Votre panier est vide');
          navigate('/catalogue');
          return;
        }
        setCart(cartData);
        setSelectedZone(cartData.zone_code || 'GUADELOUPE');

        // Load pickup locations
        const locations = await catalogAPI.getPickupLocations(cartData.zone_code);
        setPickupLocations(locations);
        if (locations.length > 0) {
          setSelectedPickup(locations[0].id);
        }

      } catch (error) {
        console.error('Checkout init error:', error);
        toast.error('Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate, cartId]);

  // Handle preparation totals change from DynamicOrderForm
  const handleTotalsChange = (totals) => {
    setPreparationTotals(totals);
  };

  const handlePreparationChange = (details) => {
    setPreparationDetails(details || []);
  };

  // Calculate final totals
  const calculateFinalTotals = () => {
    const productsHT = cart?.subtotal_ht_cents || 0;
    const preparationHT = preparationTotals?.preparation_subtotal_ht_cents || 0;
    
    // Transport fees (if delivery selected)
    const transportHT = deliveryOption?.quote?.subtotal_ht_cents || 0;
    const transportTVA = deliveryOption?.quote?.tva_cents || 0;
    const transportTTC = deliveryOption?.quote?.total_ttc_cents || 0;
    
    const totalHT = productsHT + preparationHT;
    
    // TVA (depends on zone - 0% for Guyane/Mayotte, 8.5% for others)
    const exoneratedZones = ['973', 'GUYANE', '976', 'MAYOTTE'];
    const tvaRate = exoneratedZones.includes(selectedZone) ? 0 : 8.5;
    const tva = Math.round(totalHT * tvaRate / 100);
    const totalTTC = totalHT + tva;
    
    // Grand total (KDMARCHE + LOGI'SCOP)
    const grandTotalTTC = totalTTC + transportTTC;

    return {
      productsHT,
      preparationHT,
      totalHT,
      tvaRate,
      tva,
      totalTTC,
      transportHT,
      transportTVA,
      transportTTC,
      grandTotalTTC,
      isExonerated: tvaRate === 0,
      hasDelivery: deliveryOption?.type === 'DELIVERY'
    };
  };

  const totals = calculateFinalTotals();

  // Handle signature success
  const handleSignatureSuccess = (data) => {
    setSignatureData(data);
    setSignatureComplete(true);
    setSignatureModalOpen(false);
    toast.success('Document signé avec succès !');
    setCurrentStep(4); // Move to payment step
  };

  // Handle payment
  const handlePayment = async () => {
    if (!deliveryOption) {
      toast.error('Veuillez sélectionner un mode de livraison');
      setCurrentStep(1);
      return;
    }
    
    if (!deliveryOption.terms_accepted) {
      toast.error('Veuillez accepter les conditions de transport');
      setCurrentStep(1);
      return;
    }

    if (!signatureComplete) {
      toast.error('Veuillez signer le bon de commande');
      setCurrentStep(3);
      return;
    }

    setProcessingPayment(true);
    
    try {
      // 1. Create the order first
      const order = await ordersAPIV2.create(
        cart.id, 
        selectedPickup, 
        orderNotes, 
        useInstallment && totals.totalHT >= MIN_INSTALLMENT_CENTS
      );
      
      toast.info(`Commande ${order.order_number} créée, redirection vers le paiement...`);
      
      // 2. Create Stripe checkout session
      const token = localStorage.getItem('token');
      const checkoutResponse = await fetch(`${API_URL}/api/v2/checkout/create-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          order_id: order.id,
          success_url: `${window.location.origin}/espace-acheteur?payment=success&order=${order.order_number}`,
          cancel_url: `${window.location.origin}/checkout?payment=cancelled&order=${order.order_number}`,
        }),
      });
      
      if (!checkoutResponse.ok) {
        // If Stripe session fails, try manual confirmation (for demo)
        console.log('Stripe session failed, using manual confirmation');
        
        const confirmResponse = await fetch(
          `${API_URL}/api/v2/checkout/confirm-payment?order_id=${order.id}&payment_method=${paymentMethod}`, 
          {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
          }
        );
        
        if (confirmResponse.ok) {
          const result = await confirmResponse.json();
          setOrderCreated(order);
          setPaymentSuccess(true);
          toast.success('Paiement confirmé avec succès !');
          
          // Redirect after delay
          setTimeout(() => {
            navigate('/espace-acheteur?payment=success');
          }, 2000);
        } else {
          throw new Error('Échec de la confirmation du paiement');
        }
      } else {
        const sessionData = await checkoutResponse.json();
        
        // Redirect to Stripe Checkout
        if (sessionData.checkout_url) {
          window.location.href = sessionData.checkout_url;
        } else {
          // Fallback: manual confirmation
          setOrderCreated(order);
          setPaymentSuccess(true);
          toast.success('Commande confirmée !');
          setTimeout(() => navigate('/espace-acheteur'), 2000);
        }
      }
      
    } catch (error) {
      console.error('Payment error:', error);
      toast.error(error.message || 'Erreur lors du paiement');
    } finally {
      setProcessingPayment(false);
    }
  };

  // Submit order (legacy - kept for compatibility)
  const handleSubmitOrder = async () => {
    if (!selectedPickup) {
      toast.error('Veuillez sélectionner un point d\'enlèvement');
      return;
    }

    if (!signatureComplete) {
      toast.error('Veuillez signer le bon de commande');
      setCurrentStep(3);
      return;
    }

    setSubmitting(true);
    try {
      // Create order with signature reference
      const orderData = {
        cart_id: cart.id,
        pickup_location_id: selectedPickup,
        notes: orderNotes || null,
        use_installment: useInstallment && totals.totalHT >= MIN_INSTALLMENT_CENTS,
        signature_id: signatureData?.signature_id,
        preparation_options: preparationDetails.map(d => ({
          code: d.code || d.option_id,
          qty: d.quantity || 1,
          total_ht_cents: d.total_ht_cents
        }))
      };

      const order = await ordersAPIV2.create(
        cart.id, 
        selectedPickup, 
        orderNotes, 
        useInstallment && totals.totalHT >= MIN_INSTALLMENT_CENTS
      );
      
      setOrderCreated(order);
      toast.success(`Commande ${order.order_number} créée avec succès !`);
      
      // Redirect after delay
      setTimeout(() => {
        navigate('/espace-acheteur');
      }, 3000);

    } catch (error) {
      toast.error(error.message || 'Erreur lors de la création de la commande');
    } finally {
      setSubmitting(false);
    }
  };

  // Navigate steps
  const goToStep = (step) => {
    if (step <= currentStep || step === currentStep + 1) {
      setCurrentStep(step);
    }
  };

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      // Validation before moving
      if (currentStep === 0 && (!cart || cart.items.length === 0)) {
        toast.error('Votre panier est vide');
        return;
      }
      if (currentStep === 1 && !deliveryOption) {
        toast.error('Veuillez sélectionner un mode de livraison');
        return;
      }
      // For LOGI'SCOP delivery, require transport contract acceptance
      if (currentStep === 1 && deliveryOption?.mode === 'DELIVERY' && !transportContractAccepted) {
        toast.error('Veuillez accepter le Contrat de Transport LOGI\'SCOP');
        return;
      }
      if (currentStep === 3 && !signatureComplete) {
        setSignatureModalOpen(true);
        return;
      }
      setCurrentStep(currentStep + 1);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  if (orderCreated) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Commande confirmée !</h1>
          <p className="text-white/60 mb-4">
            Votre commande <span className="text-[#D9B35A] font-mono">{orderCreated.order_number}</span> a été créée avec succès.
          </p>
          <p className="text-sm text-white/50 mb-6">
            Redirection vers votre espace acheteur...
          </p>
          <Button 
            onClick={() => navigate('/espace-acheteur')}
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
          >
            Voir mes commandes
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }} data-testid="checkout-page">
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(7,10,16,0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)'
        }}
      >
        <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="text-white/60 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Retour
            </Button>
            <div className="flex items-center gap-3">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-10 w-auto object-contain" />
              <span className="text-white/40">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-6 w-auto object-contain" />
            </div>
          </div>
          
          <h1 className="text-lg font-bold text-white">Finaliser la commande</h1>
        </div>

        {/* Steps Progress */}
        <div className="max-w-[1400px] mx-auto px-5 py-3 border-t border-white/[0.06]">
          <div className="flex items-center justify-center gap-2">
            {STEPS.map((step, idx) => {
              const StepIcon = step.icon;
              const isActive = idx === currentStep;
              const isComplete = idx < currentStep;
              
              return (
                <React.Fragment key={step.id}>
                  <button
                    onClick={() => goToStep(idx)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                      isActive 
                        ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30' 
                        : isComplete
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-white/[0.04] text-white/40 border border-white/[0.08]'
                    }`}
                    disabled={idx > currentStep + 1}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-4 h-4" />
                    )}
                    <span className="text-sm font-medium hidden sm:inline">{step.label}</span>
                  </button>
                  {idx < STEPS.length - 1 && (
                    <ChevronRight className="w-4 h-4 text-white/20" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-5 py-6">
        {/* Breadcrumb */}
        <div className="mb-4">
          <BreadcrumbPill />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Step 0: Review - Cart Summary */}
            {currentStep === 0 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Package className="w-5 h-5 text-[#D9B35A]" />
                  Récapitulatif de la commande
                </h3>
                
                {/* Cart Items */}
                <div className="space-y-3 mb-6">
                  {cart?.items?.map((item, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
                    >
                      <div>
                        <p className="text-white font-medium">{item.product_name}</p>
                        <p className="text-xs text-white/50">SKU: {item.product_sku}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-white">{item.quantity} x {formatCurrency(item.price_ht_cents)}</p>
                        <p className="text-[#D9B35A] font-semibold">{formatCurrency(item.line_total_ht_cents)}</p>
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="border-t border-white/10 pt-4">
                  <div className="flex justify-between text-white/70 mb-2">
                    <span>Sous-total produits HT</span>
                    <span>{formatCurrency(cart?.subtotal_ht_cents || 0)}</span>
                  </div>
                  <div className="flex justify-between text-white font-semibold">
                    <span>Total articles</span>
                    <span>{cart?.items?.reduce((sum, i) => sum + i.quantity, 0) || 0}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Step 1: Delivery Options */}
            {currentStep === 1 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Truck className="w-5 h-5 text-[#57D19A]" />
                  Mode de livraison LOGI'SCOP
                </h3>
                
                {/* Zone Selection */}
                <div className="mb-6">
                  <Label className="text-white/70 mb-2 block">Zone géographique</Label>
                  <Select value={selectedZone} onValueChange={setSelectedZone}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {zones.map(z => (
                        <SelectItem key={z.code} value={z.code}>{z.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Delivery Options Selector */}
                <DeliveryOptionsSelector
                  zoneCode={selectedZone}
                  weightKg={cart?.total_weight_kg || 10}
                  volumeM3={cart?.total_volume_m3 || 0.1}
                  itemsCount={cart?.items?.length || 1}
                  onOptionChange={setDeliveryOption}
                  initialOption={deliveryOption}
                />

                {/* Transport Contract Acceptance (if LOGI'SCOP delivery) */}
                {deliveryOption?.mode === 'DELIVERY' && (
                  <div className="mt-6 p-5 rounded-xl bg-amber-500/5 border border-amber-500/20">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id="transport-contract"
                        checked={transportContractAccepted}
                        onCheckedChange={setTransportContractAccepted}
                        className="mt-1 border-amber-500/40 data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500"
                        data-testid="transport-contract-checkbox"
                      />
                      <div className="flex-1">
                        <Label 
                          htmlFor="transport-contract" 
                          className="text-sm text-white/90 font-medium cursor-pointer leading-relaxed"
                        >
                          J'ai lu et j'accepte le{' '}
                          <Link 
                            to="/legal/contrat-transport" 
                            target="_blank"
                            className="text-amber-400 hover:text-amber-300 underline underline-offset-2"
                          >
                            Contrat de Transport LOGI'SCOP
                          </Link>
                        </Label>
                        <p className="text-xs text-white/50 mt-2 leading-relaxed">
                          La livraison LOGI'SCOP est une prestation de transport indépendante, 
                          distincte de la vente des marchandises, exécutée par un opérateur logistique ESS.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Preparation Options */}
            {currentStep === 2 && (
              <DynamicOrderForm
                products={products}
                zoneCode={selectedZone}
                orderData={{
                  CLIENT_LEGAL_NAME: user?.company_name || 'Organisation',
                  CLIENT_ADDRESS: user?.address || '',
                  CLIENT_SIRET: user?.siret || '',
                  CLIENT_CONTACT: user?.contact_name || user?.email || ''
                }}
                showStamp={false}
                onTotalsChange={handleTotalsChange}
                onPreparationChange={handlePreparationChange}
              />
            )}

            {/* Step 3: Signature */}
            {currentStep === 3 && (
              <div className="glass-panel-soft rounded-[18px] p-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <FileSignature className="w-5 h-5 text-purple-400" />
                  Signature électronique
                </h2>
                
                {signatureComplete ? (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </div>
                    <p className="text-lg font-medium text-white mb-2">Document signé</p>
                    <p className="text-sm text-white/60 mb-4">
                      Votre bon de commande a été signé électroniquement.
                    </p>
                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                      <Shield className="w-3 h-3 mr-1" />
                      Signature eIDAS niveau AES
                    </Badge>
                    {signatureData?.signature_hash && (
                      <p className="text-xs text-white/40 mt-4 font-mono">
                        Hash: {signatureData.signature_hash?.substring(0, 32)}...
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <FileSignature className="w-8 h-8 text-purple-400" />
                    </div>
                    <p className="text-lg font-medium text-white mb-2">Signature requise</p>
                    <p className="text-sm text-white/60 mb-6">
                      Signez votre bon de commande par SMS (code OTP) pour valider votre commande.
                    </p>
                    <Button 
                      onClick={() => setSignatureModalOpen(true)}
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                    >
                      <FileSignature className="w-4 h-4 mr-2" />
                      Signer le bon de commande
                    </Button>
                    <p className="text-xs text-white/40 mt-4">
                      Conformité eIDAS niveau AES (Advanced Electronic Signature)
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Payment */}
            {currentStep === 4 && (
              <div className="space-y-6">
                {/* Payment Method Selection */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-[#D9B35A]" />
                    Mode de paiement
                  </h2>
                  
                  <div className="space-y-4">
                    {/* Installment Option */}
                    {totals.totalHT >= MIN_INSTALLMENT_CENTS && (
                      <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                        useInstallment 
                          ? 'border-purple-500 bg-purple-500/10' 
                          : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                      }`}
                        onClick={() => setUseInstallment(!useInstallment)}
                      >
                        <div className="flex items-center gap-3">
                          <Checkbox 
                            checked={useInstallment} 
                            onCheckedChange={setUseInstallment}
                            className="border-white/30"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-white flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-purple-400" />
                              Paiement en 4× sans frais cachés
                            </p>
                            <p className="text-xs text-white/50 mt-1">
                              À partir de 5 500€ HT. Frais: 20% HT + TVA
                            </p>
                          </div>
                          <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                            4× {formatCurrency(Math.ceil(totals.totalTTC / 4))}
                          </Badge>
                        </div>
                      </div>
                    )}
                    
                    {/* Card Payment */}
                    <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      !useInstallment && paymentMethod === 'card'
                        ? 'border-[#D9B35A] bg-[#D9B35A]/10' 
                        : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                    }`}
                      onClick={() => { setUseInstallment(false); setPaymentMethod('card'); }}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox 
                          checked={!useInstallment && paymentMethod === 'card'} 
                          onCheckedChange={() => { setUseInstallment(false); setPaymentMethod('card'); }}
                          className="border-white/30"
                        />
                        <div className="flex-1">
                          <p className="font-medium text-white flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-[#D9B35A]" />
                            Carte bancaire
                          </p>
                          <p className="text-xs text-white/50 mt-1">
                            Visa, Mastercard, American Express
                          </p>
                        </div>
                        <div className="flex gap-1">
                          <div className="w-8 h-5 rounded bg-[#1A1F71] flex items-center justify-center">
                            <span className="text-[8px] text-white font-bold">VISA</span>
                          </div>
                          <div className="w-8 h-5 rounded bg-gradient-to-r from-red-500 to-yellow-500 flex items-center justify-center">
                            <span className="text-[6px] text-white font-bold">MC</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* SEPA Payment */}
                    <div className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      !useInstallment && paymentMethod === 'sepa'
                        ? 'border-blue-500 bg-blue-500/10' 
                        : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20'
                    }`}
                      onClick={() => { setUseInstallment(false); setPaymentMethod('sepa'); }}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox 
                          checked={!useInstallment && paymentMethod === 'sepa'} 
                          onCheckedChange={() => { setUseInstallment(false); setPaymentMethod('sepa'); }}
                          className="border-white/30"
                        />
                        <div className="flex-1">
                          <p className="font-medium text-white flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-blue-400" />
                            Prélèvement SEPA
                          </p>
                          <p className="text-xs text-white/50 mt-1">
                            Débit automatique depuis votre compte bancaire
                          </p>
                        </div>
                        <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">SEPA</Badge>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Stripe Payment Form */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                      <Lock className="w-4 h-4 text-emerald-400" />
                      Paiement sécurisé
                    </h3>
                    <div className="flex items-center gap-2">
                      <img 
                        src="https://stripe.com/img/v3/home/twitter.png" 
                        alt="Stripe" 
                        className="h-6 opacity-60"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                      <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">
                        SSL 256-bit
                      </Badge>
                    </div>
                  </div>

                  {/* Payment Info */}
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white/60">Montant à régler</span>
                      <span className="text-2xl font-bold text-[#D9B35A]">
                        {formatCurrency(useInstallment ? totals.installmentTotal : totals.totalTTC)}
                      </span>
                    </div>
                    {useInstallment && (
                      <p className="text-xs text-purple-400">
                        Dont {formatCurrency(totals.installmentFees)} de frais (4 échéances de {formatCurrency(Math.ceil((totals.installmentTotal || totals.totalTTC) / 4))})
                      </p>
                    )}
                  </div>

                  {/* Payment Action */}
                  <Button
                    onClick={handlePayment}
                    disabled={processingPayment || !signatureComplete}
                    className="w-full bg-gradient-to-r from-[#D9B35A] to-[#c9a34a] hover:from-[#c9a34a] hover:to-[#b9934a] text-black font-semibold h-12"
                    data-testid="pay-now-btn"
                  >
                    {processingPayment ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Traitement en cours...
                      </>
                    ) : (
                      <>
                        <Lock className="w-4 h-4 mr-2" />
                        Payer {formatCurrency(useInstallment ? totals.installmentTotal : totals.totalTTC)}
                      </>
                    )}
                  </Button>

                  {!signatureComplete && (
                    <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <p className="text-xs text-amber-400 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        Veuillez d'abord signer le bon de commande à l'étape précédente.
                      </p>
                    </div>
                  )}

                  <p className="text-xs text-white/40 text-center mt-4">
                    En cliquant sur "Payer", vous acceptez nos conditions générales de vente et autorisez le prélèvement du montant indiqué.
                  </p>
                </div>

                {/* Notes */}
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Notes (optionnel)</h3>
                  <Input
                    placeholder="Instructions particulières pour la commande..."
                    value={orderNotes}
                    onChange={(e) => setOrderNotes(e.target.value)}
                    className="bg-white/[0.04] border-white/10"
                    data-testid="order-notes-input"
                  />
                </div>

                {/* EXW Warning */}
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                  <p className="text-sm text-amber-400">
                    <strong>Incoterm EXW :</strong> L'enlèvement, le transport et les formalités douanières sont à votre charge.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar - Order Summary */}
          <div className="lg:col-span-1">
            <div className="sticky top-[140px] glass-panel-soft rounded-[18px] p-6">
              <h3 className="text-lg font-bold text-white mb-4">Récapitulatif</h3>
              
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">Marchandises HT</span>
                  <span className="font-medium text-white">{formatCurrency(totals.productsHT)}</span>
                </div>
                
                {totals.preparationHT > 0 && (
                  <div className="flex justify-between text-emerald-400">
                    <span>Frais préparation HT</span>
                    <span className="font-medium">{formatCurrency(totals.preparationHT)}</span>
                  </div>
                )}
                
                <div className="flex justify-between border-t border-white/[0.08] pt-3">
                  <span className="text-white/60">Total HT</span>
                  <span className="font-bold text-white">{formatCurrency(totals.totalHT)}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-white/60">
                    TVA {totals.isExonerated ? '(exonérée)' : `(${totals.tvaRate}%)`}
                  </span>
                  <span className={totals.isExonerated ? 'text-emerald-400' : 'text-white'}>
                    {formatCurrency(totals.tva)}
                  </span>
                </div>
                
                <div className="flex justify-between border-t border-white/[0.08] pt-3">
                  <span className="font-semibold text-white">Total TTC</span>
                  <span className="text-2xl font-bold text-[#D9B35A]">{formatCurrency(totals.totalTTC)}</span>
                </div>
              </div>

              {/* Status badges */}
              <div className="mt-6 space-y-2">
                <Badge className="w-full justify-center bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                  <Truck className="w-3 h-3 mr-1" />
                  Incoterm EXW
                </Badge>
                {signatureComplete && (
                  <Badge className="w-full justify-center bg-purple-500/20 text-purple-400 border-purple-500/30">
                    <Shield className="w-3 h-3 mr-1" />
                    Signé électroniquement
                  </Badge>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-6 space-y-3">
                {currentStep < 4 ? (
                  <Button 
                    onClick={nextStep}
                    className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
                  >
                    Continuer
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                ) : (
                  <Button 
                    onClick={handleSubmitOrder}
                    disabled={submitting || !signatureComplete}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    {submitting ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                    )}
                    Confirmer la commande
                  </Button>
                )}
                
                {currentStep > 0 && (
                  <Button 
                    variant="outline"
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="w-full border-white/10 text-white/70"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Étape précédente
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Signature Modal */}
      <SMSSignatureModal
        isOpen={signatureModalOpen}
        onClose={() => setSignatureModalOpen(false)}
        onSuccess={handleSignatureSuccess}
        documentTitle="Bon de Commande B2B"
        documentDescription={`Commande EXW - Zone ${selectedZone} - ${cart?.items?.length || 0} article(s) - Total: ${formatCurrency(totals.totalTTC)} TTC`}
        signerInfo={{
          name: user?.contact_name || user?.email,
          email: user?.email,
          phone: user?.phone || '',
          company: user?.company_name
        }}
      />
    </div>
  );
}
