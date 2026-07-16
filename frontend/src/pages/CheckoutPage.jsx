import i18n from '@/i18n';
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
import { formatCurrency, STEPS } from '../components/checkout/checkoutUtils';
import { CheckoutProgress } from '../components/checkout/CheckoutProgress';
import { ReviewStep, DeliveryStep, PreparationStep, SignatureStep } from '../components/checkout/CheckoutSteps';
import { PaymentStep, OrderSummarySidebar } from '../components/checkout/CheckoutPayment';

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
    toast.success(i18n.t('checkout.toast_document_signe'));
    setCurrentStep(4); // Move to payment step
  };

  // Handle payment
  const handlePayment = async () => {
    if (!deliveryOption) {
      toast.error(i18n.t('checkout.toast_select_livraison'));
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
      
      toast.info(i18n.t('checkout.toast_commande_creee_redirection', { number: order.order_number }));
      
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
          toast.success(i18n.t('checkout.toast_paiement_confirme'));
          
          // Redirect after delay
          setTimeout(() => {
            navigate('/espace-acheteur?payment=success');
          }, 2000);
        } else {
          throw new Error(i18n.t('checkout.toast_echec_confirmation'));
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
          toast.success(i18n.t('checkout.toast_commande_confirmee'));
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
      toast.error(i18n.t('checkout.toast_select_enlevement'));
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
      toast.success(i18n.t('checkout.toast_commande_creee', { number: order.order_number }));
      
      // Redirect after delay
      setTimeout(() => {
        navigate('/espace-acheteur');
      }, 3000);

    } catch (error) {
      toast.error(error.message || i18n.t('checkout.toast_erreur_creation'));
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
        toast.error(i18n.t('checkout.toast_select_livraison'));
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
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  if (orderCreated) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">{i18n.t('checkout.commande_confirmee')}</h1>
          <p className="text-white/60 mb-4">
            {i18n.t('checkout.votre_commande_prefix')} <span className="text-[#D9B35A] font-mono">{orderCreated.order_number}</span> {i18n.t('checkout.creee_avec_succes_suffix')}
          </p>
          <p className="text-sm text-white/50 mb-6">
            {i18n.t('checkout.redirection_vers_votre_espace')}
          </p>
          <Button 
            onClick={() => navigate('/espace-acheteur')}
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
          >
            {i18n.t('checkout.voir_mes_commandes')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="checkout-page">
      <CheckoutProgress currentStep={currentStep} goToStep={goToStep} navigate={navigate} />

      <div className="max-w-[1400px] mx-auto px-5 py-6">
        {/* Breadcrumb */}
        <div className="mb-4">
          <BreadcrumbPill />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <ReviewStep currentStep={currentStep} cart={cart} />
            <DeliveryStep currentStep={currentStep} cart={cart} zones={zones} selectedZone={selectedZone} setSelectedZone={setSelectedZone} deliveryOption={deliveryOption} setDeliveryOption={setDeliveryOption} transportContractAccepted={transportContractAccepted} setTransportContractAccepted={setTransportContractAccepted} />
            <PreparationStep currentStep={currentStep} user={user} products={products} selectedZone={selectedZone} handleTotalsChange={handleTotalsChange} handlePreparationChange={handlePreparationChange} />
            <SignatureStep currentStep={currentStep} signatureComplete={signatureComplete} signatureData={signatureData} setSignatureModalOpen={setSignatureModalOpen} />
            <PaymentStep currentStep={currentStep} totals={totals} useInstallment={useInstallment} setUseInstallment={setUseInstallment} paymentMethod={paymentMethod} setPaymentMethod={setPaymentMethod} orderNotes={orderNotes} setOrderNotes={setOrderNotes} signatureComplete={signatureComplete} processingPayment={processingPayment} handlePayment={handlePayment} />
          </div>

          <OrderSummarySidebar currentStep={currentStep} totals={totals} signatureComplete={signatureComplete} submitting={submitting} setCurrentStep={setCurrentStep} handleSubmitOrder={handleSubmitOrder} nextStep={nextStep} />
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
