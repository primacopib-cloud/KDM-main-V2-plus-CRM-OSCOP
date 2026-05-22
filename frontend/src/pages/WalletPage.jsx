import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, Wallet, MapPin, Plus, Minus, CreditCard, TrendingUp,
  TrendingDown, Clock, CheckCircle2, AlertCircle, Loader2, History,
  Globe, Lock, Unlock, ChevronRight, RefreshCw, ShoppingCart, Sparkles,
  ExternalLink, Building2, Landmark, Copy, CheckCheck, FileText
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';

import { partners } from '../data/mock';
import { authAPI, walletAPIV2, zonesAPIV2, paymentAPI } from '../services/api';

// Format credits
const formatCredits = (amount) => {
  if (amount === null || amount === undefined) return '---';
  return amount.toLocaleString('fr-FR');
};

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Transaction type config
const TX_TYPES = {
  CREDIT: { label: 'Crédit', icon: TrendingUp, color: 'text-green-400' },
  DEBIT: { label: 'Débit', icon: TrendingDown, color: 'text-red-400' },
  TOPUP: { label: 'Recharge', icon: Plus, color: 'text-blue-400' },
  SUBSCRIPTION: { label: 'Abonnement', icon: CreditCard, color: 'text-purple-400' },
  REFUND: { label: 'Remboursement', icon: RefreshCw, color: 'text-orange-400' },
};

// Zone type config
const ZONE_TYPES = {
  OM: { label: 'Outre-Mer', color: 'bg-blue-500/20 text-blue-400' },
  EU: { label: 'Europe', color: 'bg-green-500/20 text-green-400' },
  CARIB: { label: 'Caraïbes', color: 'bg-purple-500/20 text-purple-400' },
  AFRICA: { label: 'Afrique', color: 'bg-orange-500/20 text-orange-400' },
};

export default function WalletPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [orgId, setOrgId] = useState(null);
  
  // Wallet data
  const [wallet, setWallet] = useState(null);
  const [ledger, setLedger] = useState([]);
  
  // Zones data
  const [allZones, setAllZones] = useState([]);
  const [entitledZones, setEntitledZones] = useState([]);
  
  // Top-up dialog (legacy - keep for org wallet)
  const [topupOpen, setTopupOpen] = useState(false);
  const [topupAmount, setTopupAmount] = useState(100);
  const [topupLoading, setTopupLoading] = useState(false);
  
  // Zone add dialog
  const [zoneDialogOpen, setZoneDialogOpen] = useState(false);
  const [selectedZone, setSelectedZone] = useState(null);
  const [zoneLoading, setZoneLoading] = useState(false);
  
  // Payment states
  const [packages, setPackages] = useState([]);
  const [buyCreditsOpen, setBuyCreditsOpen] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [paymentChecking, setPaymentChecking] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('card'); // card, transfer, sepa
  
  // Bank transfer states
  const [bankDetails, setBankDetails] = useState(null);
  const [transferReference, setTransferReference] = useState(null);
  const [companyName, setCompanyName] = useState('');
  const [copiedField, setCopiedField] = useState(null);
  
  // SEPA states
  const [sepaIban, setSepaIban] = useState('');
  const [sepaName, setSepaName] = useState('');
  const [sepaEmail, setSepaEmail] = useState('');
  const [sepaLoading, setSepaLoading] = useState(false);

  // Poll payment status (stable: only depends on `navigate`)
  const pollPaymentStatus = useCallback(async (sessionId, attempts = 0) => {
    const maxAttempts = 10;
    const pollInterval = 2000;

    if (attempts >= maxAttempts) {
      setPaymentChecking(false);
      toast.error('Vérification du paiement expirée. Vérifiez votre email.');
      navigate('/wallet', { replace: true });
      return;
    }

    try {
      const status = await paymentAPI.getStatus(sessionId);

      if (status.payment_status === 'paid' && status.credited) {
        setPaymentChecking(false);
        toast.success(`${status.credits} crédits ajoutés avec succès !`);
        navigate('/wallet', { replace: true });
        const userData = await authAPI.getMe();
        setUser(userData);
        return;
      } else if (status.status === 'EXPIRED') {
        setPaymentChecking(false);
        toast.error('Session de paiement expirée');
        navigate('/wallet', { replace: true });
        return;
      }

      // Continue polling
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Payment status error:', error);
      setPaymentChecking(false);
      toast.error('Erreur vérification paiement');
      navigate('/wallet', { replace: true });
    }
  }, [navigate]);

  // Check for payment return
  useEffect(() => {
    const paymentStatus = searchParams.get('payment');
    const sessionId = searchParams.get('session_id');

    if (paymentStatus === 'success' && sessionId) {
      setPaymentChecking(true);
      pollPaymentStatus(sessionId);
    } else if (paymentStatus === 'cancelled') {
      toast.error('Paiement annulé');
      navigate('/wallet', { replace: true });
    }
  }, [searchParams, navigate, pollPaymentStatus]);

  // Copy to clipboard
  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
    toast.success('Copié !');
  };

  // Load data — runs once on mount; `navigate` is stable (react-router)
  useEffect(() => {
    const init = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion?redirect=/wallet');
        return;
      }

      try {
        const userData = await authAPI.getMe();
        setUser(userData);

        // Load Stripe packages
        const packagesData = await paymentAPI.getPackages().catch(() => ({ packages: [] }));
        setPackages(packagesData.packages || []);

        // Get org ID from user's membership
        const orgIdValue = userData.org_id || userData.organization_id;
        if (orgIdValue) {
          setOrgId(orgIdValue);

          // Load wallet and zones in parallel
          const [walletData, ledgerData, zonesData, entitlementsData] = await Promise.all([
            walletAPIV2.get(orgIdValue).catch(() => null),
            walletAPIV2.getLedger(orgIdValue, 50).catch(() => []),
            zonesAPIV2.list().catch(() => []),
            zonesAPIV2.getOrgEntitlements(orgIdValue).catch(() => []),
          ]);

          setWallet(walletData);
          setLedger(ledgerData);
          setAllZones(zonesData);
          setEntitledZones(entitlementsData);
        }
      } catch (error) {
        console.error('Init error:', error);
        toast.error('Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  // Refresh wallet
  const refreshWallet = async () => {
    if (!orgId) return;
    try {
      const [walletData, ledgerData] = await Promise.all([
        walletAPIV2.get(orgId),
        walletAPIV2.getLedger(orgId, 50),
      ]);
      setWallet(walletData);
      setLedger(ledgerData);
      toast.success('Wallet actualisé');
    } catch (error) {
      toast.error('Erreur lors de l\'actualisation');
    }
  };

  // Handle card payment (Stripe checkout)
  const handleCardPayment = async (pkg) => {
    setSelectedPackage(pkg);
    setCheckoutLoading(true);
    
    try {
      const response = await paymentAPI.createCheckout(pkg.id);
      window.location.href = response.checkout_url;
    } catch (error) {
      toast.error(error.message || 'Erreur création paiement');
      setCheckoutLoading(false);
    }
  };

  // Handle bank transfer
  const handleBankTransfer = async (pkg) => {
    if (!companyName.trim()) {
      toast.error('Veuillez saisir le nom de votre entreprise');
      return;
    }
    
    setSelectedPackage(pkg);
    setCheckoutLoading(true);
    
    try {
      const response = await paymentAPI.createBankTransfer(pkg.id, companyName);
      setTransferReference(response);
      setBankDetails(response.bank_details);
      toast.success('Référence de virement générée');
    } catch (error) {
      toast.error(error.message || 'Erreur création virement');
    } finally {
      setCheckoutLoading(false);
    }
  };

  // Handle SEPA setup
  const handleSepaSetup = async (pkg) => {
    if (!sepaIban.trim() || !sepaName.trim() || !sepaEmail.trim()) {
      toast.error('Veuillez remplir tous les champs SEPA');
      return;
    }
    
    setSelectedPackage(pkg);
    setSepaLoading(true);
    
    try {
      const response = await paymentAPI.createSepaSetup(pkg.id, sepaIban, sepaName, sepaEmail);
      toast.success('Mandat SEPA créé. Confirmation en cours...');
      
      // Try to confirm immediately
      const confirmResponse = await paymentAPI.confirmSepaPayment(response.setup_id);
      if (confirmResponse.status === 'succeeded') {
        toast.success(`${confirmResponse.credits} crédits ajoutés !`);
        const userData = await authAPI.getMe();
        setUser(userData);
        setBuyCreditsOpen(false);
      } else {
        toast.info('Paiement SEPA en cours de traitement (2-14 jours)');
      }
    } catch (error) {
      toast.error(error.message || 'Erreur SEPA');
    } finally {
      setSepaLoading(false);
    }
  };

  // Open buy credits with bank details preloaded
  const openBuyCredits = async () => {
    setBuyCreditsOpen(true);
    setTransferReference(null);
    // Load bank details if not already loaded
    if (!bankDetails) {
      try {
        const details = await paymentAPI.getBankDetails();
        setBankDetails(details.bank_details);
      } catch (e) {
        console.error('Failed to load bank details:', e);
      }
    }
  };

  // Handle top-up (legacy for org wallet)
  const handleTopup = async () => {
    if (!orgId || topupAmount < 10) {
      toast.error('Montant minimum: 10 crédits');
      return;
    }

    setTopupLoading(true);
    try {
      await walletAPIV2.topup(orgId, topupAmount);
      toast.success(`${topupAmount} crédits ajoutés avec succès`);
      setTopupOpen(false);
      setTopupAmount(100);
      refreshWallet();
    } catch (error) {
      toast.error(error.message || 'Erreur lors de la recharge');
    } finally {
      setTopupLoading(false);
    }
  };

  // Handle zone add
  const handleAddZone = async () => {
    if (!orgId || !selectedZone) return;

    setZoneLoading(true);
    try {
      await zonesAPIV2.addEntitlement(orgId, selectedZone.id);
      toast.success(`Zone ${selectedZone.name} activée`);
      setZoneDialogOpen(false);
      setSelectedZone(null);
      
      // Refresh entitlements
      const entitlementsData = await zonesAPIV2.getOrgEntitlements(orgId);
      setEntitledZones(entitlementsData);
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'activation');
    } finally {
      setZoneLoading(false);
    }
  };

  // Get available zones (not entitled yet)
  const availableZones = allZones.filter(z => 
    !entitledZones.some(e => e.zone_id === z.id)
  );

  if (loading || paymentChecking) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
        {paymentChecking && (
          <p className="text-white/60 text-sm">Vérification du paiement en cours...</p>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="wallet-page">
      {/* Header - Ultra compact */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.96)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1160px] mx-auto px-4 py-1 flex items-center justify-between h-10">
          <div className="flex items-center gap-2">
            <Link to="/dashboard" className="text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" />
            </Link>
            <div className="flex items-center gap-1">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-5 w-auto object-contain" />
              <span className="text-white/30 text-[10px]">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-4 w-auto object-contain" />
            </div>
          </div>
          
          <div className="flex items-center gap-1.5">
            {user && (
              <span className="text-[#D9B35A] text-xs font-medium">
                {formatCredits(user.credits || 0)} crédits
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={refreshWallet} className="h-6 w-6 p-0 hover:bg-white/10">
              <RefreshCw className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-4">
        {/* Title */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold mb-1">Wallet & Crédits</h1>
          <p className="text-white/60 text-sm">Gérez vos crédits et achetez des packs</p>
        </div>

        {/* User Credits Card (always visible) */}
        <div className="mb-6 glass-panel-soft rounded-[18px] p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white/60 mb-1">Vos crédits personnels</p>
              <p className="text-3xl font-bold text-[#D9B35A]">
                {formatCredits(user?.credits || 0)}
                <span className="text-base font-normal text-white/50 ml-2">crédits</span>
              </p>
            </div>
            <Button 
              onClick={openBuyCredits}
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
              data-testid="buy-credits-btn"
            >
              <ShoppingCart className="w-4 h-4 mr-2" />
              Acheter des crédits
            </Button>
          </div>
        </div>

        {/* No org info */}
        {!orgId && (
          <div className="mb-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-400">Organisation B2B</p>
                <p className="text-sm text-blue-400/80">
                  Pour accéder au wallet organisation et aux zones, associez-vous à une organisation B2B.
                </p>
                <Link to="/onboarding" className="text-sm text-blue-400 underline mt-2 inline-block">
                  Demander l'adhésion →
                </Link>
              </div>
            </div>
          </div>
        )}

        {orgId && (
          <Tabs defaultValue="wallet" className="space-y-6">
            <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1">
              <TabsTrigger 
                value="wallet"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
              >
                <Wallet className="w-4 h-4 mr-2" />
                Wallet Org
              </TabsTrigger>
              <TabsTrigger 
                value="zones"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
              >
                <MapPin className="w-4 h-4 mr-2" />
                Zones ({entitledZones.length})
              </TabsTrigger>
            </TabsList>

            {/* Wallet Tab */}
            <TabsContent value="wallet" className="space-y-6">
              {/* Balance Card */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="glass-panel-soft rounded-[18px] p-6 md:col-span-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-white/60 mb-2">Solde disponible</p>
                      <p className="text-4xl font-bold text-[#D9B35A]">
                        {formatCredits(wallet?.balance)} 
                        <span className="text-lg font-normal text-white/50 ml-2">crédits</span>
                      </p>
                      {wallet?.pending_balance > 0 && (
                        <p className="text-sm text-white/50 mt-1">
                          + {formatCredits(wallet?.pending_balance)} en attente
                        </p>
                      )}
                    </div>
                    <Button 
                      onClick={() => setTopupOpen(true)}
                      className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Recharger
                    </Button>
                  </div>
                </div>

                <div className="glass-panel-soft rounded-[18px] p-6">
                  <p className="text-sm text-white/60 mb-4">Statistiques</p>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-white/70 text-sm">Total crédité</span>
                      <span className="font-semibold text-green-400">
                        +{formatCredits(wallet?.total_credited || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-white/70 text-sm">Total débité</span>
                      <span className="font-semibold text-red-400">
                        -{formatCredits(wallet?.total_debited || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Transaction History */}
              <div className="glass-panel-soft rounded-[18px] p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <History className="w-4 h-4 text-white/50" />
                    Historique des transactions
                  </h3>
                  <Badge variant="outline" className="text-white/50 border-white/20">
                    {ledger.length} transactions
                  </Badge>
                </div>

                {ledger.length === 0 ? (
                  <div className="text-center py-8 text-white/50">
                    <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune transaction</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {ledger.map((tx, idx) => {
                      const typeConfig = TX_TYPES[tx.type] || TX_TYPES.CREDIT;
                      const Icon = typeConfig.icon;
                      const isCredit = tx.amount > 0;

                      return (
                        <div 
                          key={tx.id || idx}
                          className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isCredit ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                              <Icon className={`w-4 h-4 ${typeConfig.color}`} />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-white/90">{tx.description || typeConfig.label}</p>
                              <p className="text-xs text-white/50">{formatDate(tx.created_at)}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`font-semibold ${isCredit ? 'text-green-400' : 'text-red-400'}`}>
                              {isCredit ? '+' : ''}{formatCredits(tx.amount)}
                            </p>
                            <p className="text-xs text-white/40">
                              Solde: {formatCredits(tx.balance_after)}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Zones Tab */}
            <TabsContent value="zones" className="space-y-6">
              {/* Entitled Zones */}
              <div className="glass-panel-soft rounded-[18px] p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Unlock className="w-4 h-4 text-[#57D19A]" />
                    Zones activées
                  </h3>
                  <Badge className="bg-[#57D19A]/20 text-[#57D19A]">
                    {entitledZones.length} zone{entitledZones.length > 1 ? 's' : ''}
                  </Badge>
                </div>

                {entitledZones.length === 0 ? (
                  <div className="text-center py-8 text-white/50">
                    <MapPin className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune zone activée</p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-4 border-white/10"
                      onClick={() => setZoneDialogOpen(true)}
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Ajouter une zone
                    </Button>
                  </div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-3">
                    {entitledZones.map((entitlement, idx) => {
                      const zone = allZones.find(z => z.id === entitlement.zone_id) || {};
                      const typeConfig = ZONE_TYPES[zone.zone_type] || ZONE_TYPES.OM;

                      return (
                        <div 
                          key={entitlement.id || idx}
                          className="p-4 rounded-xl bg-[#57D19A]/5 border border-[#57D19A]/20"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-white/90">{zone.name || entitlement.zone_id}</p>
                              <p className="text-xs text-white/50 mt-1">{zone.code}</p>
                            </div>
                            <Badge className={typeConfig.color}>
                              {typeConfig.label}
                            </Badge>
                          </div>
                          <div className="mt-3 flex items-center gap-2 text-xs text-white/50">
                            <CheckCircle2 className="w-3 h-3 text-[#57D19A]" />
                            <span>Activée le {formatDate(entitlement.created_at)}</span>
                          </div>
                          {zone.exw_only && (
                            <p className="text-xs text-amber-400 mt-2">
                              ⚠️ EXW uniquement
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Available Zones */}
              {availableZones.length > 0 && (
                <div className="glass-panel-soft rounded-[18px] p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Lock className="w-4 h-4 text-white/50" />
                      Zones disponibles
                    </h3>
                    <Badge variant="outline" className="text-white/50 border-white/20">
                      {availableZones.length} zone{availableZones.length > 1 ? 's' : ''}
                    </Badge>
                  </div>

                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {availableZones.map(zone => {
                      const typeConfig = ZONE_TYPES[zone.zone_type] || ZONE_TYPES.OM;

                      return (
                        <div 
                          key={zone.id}
                          className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors cursor-pointer"
                          onClick={() => {
                            setSelectedZone(zone);
                            setZoneDialogOpen(true);
                          }}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-white/70">{zone.name}</p>
                              <p className="text-xs text-white/40 mt-1">{zone.code}</p>
                            </div>
                            <ChevronRight className="w-4 h-4 text-white/30" />
                          </div>
                          <Badge className={`${typeConfig.color} mt-2`}>
                            {typeConfig.label}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>

      {/* Top-up Dialog */}
      <Dialog open={topupOpen} onOpenChange={setTopupOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-[#D9B35A]" />
              Recharger le wallet
            </DialogTitle>
            <DialogDescription className="text-white/60">
              Ajoutez des crédits à votre compte O'SCOP
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Montant (crédits)</label>
              <Input
                type="number"
                min={10}
                step={10}
                value={topupAmount}
                onChange={(e) => setTopupAmount(parseInt(e.target.value) || 0)}
                className="bg-white/[0.04] border-white/10 text-xl font-bold text-center"
              />
            </div>

            {/* Quick amounts */}
            <div className="flex gap-2">
              {[50, 100, 200, 500].map(amount => (
                <button
                  key={amount}
                  onClick={() => setTopupAmount(amount)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                    topupAmount === amount
                      ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
                      : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
                  }`}
                >
                  {amount}
                </button>
              ))}
            </div>

            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
              <p className="text-xs text-white/50">
                Les crédits sont non remboursables et non convertibles en espèces. 
                Ils permettent d'accéder aux services premium O'SCOP.
              </p>
            </div>
          </div>

          <DialogFooter className="flex gap-3">
            <Button variant="outline" onClick={() => setTopupOpen(false)} className="border-white/10">
              Annuler
            </Button>
            <Button
              onClick={handleTopup}
              disabled={topupLoading || topupAmount < 10}
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
            >
              {topupLoading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Ajouter {topupAmount} crédits
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Zone Add Dialog */}
      <Dialog open={zoneDialogOpen} onOpenChange={setZoneDialogOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-[#57D19A]" />
              Activer une zone
            </DialogTitle>
            <DialogDescription className="text-white/60">
              {selectedZone 
                ? `Activer l'accès à ${selectedZone.name}`
                : 'Sélectionnez une zone à activer'
              }
            </DialogDescription>
          </DialogHeader>

          {selectedZone && (
            <div className="py-4">
              <div className="p-4 rounded-xl bg-[#57D19A]/5 border border-[#57D19A]/20">
                <p className="font-semibold text-white/90">{selectedZone.name}</p>
                <p className="text-sm text-white/60 mt-1">{selectedZone.code}</p>
                {selectedZone.exw_only && (
                  <p className="text-xs text-amber-400 mt-2">
                    ⚠️ Cette zone fonctionne en Incoterm EXW uniquement
                  </p>
                )}
              </div>

              <div className="mt-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
                <p className="text-xs text-white/50">
                  L'activation d'une zone vous permet d'accéder aux prix et de passer 
                  des commandes pour les produits disponibles dans cette zone.
                </p>
              </div>
            </div>
          )}

          <DialogFooter className="flex gap-3">
            <Button 
              variant="outline" 
              onClick={() => {
                setZoneDialogOpen(false);
                setSelectedZone(null);
              }} 
              className="border-white/10"
            >
              Annuler
            </Button>
            <Button
              onClick={handleAddZone}
              disabled={zoneLoading || !selectedZone}
              className="bg-[#57D19A] hover:bg-[#47c18a] text-black"
            >
              {zoneLoading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              )}
              Activer la zone
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Buy Credits Dialog - Multi Payment Methods */}
      <Dialog open={buyCreditsOpen} onOpenChange={(open) => {
        setBuyCreditsOpen(open);
        if (!open) {
          setTransferReference(null);
          setSelectedPackage(null);
          setPaymentMethod('card');
        }
      }}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto bg-[#0a0d14] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
              Acheter des crédits
            </DialogTitle>
            <DialogDescription className="text-white/50">
              Choisissez votre mode de paiement et sélectionnez un pack
            </DialogDescription>
          </DialogHeader>

          {/* Payment Method Tabs */}
          <Tabs value={paymentMethod} onValueChange={setPaymentMethod} className="mt-2">
            <TabsList className="grid grid-cols-3 bg-white/[0.04] border border-white/[0.08]">
              <TabsTrigger value="card" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
                <CreditCard className="w-4 h-4 mr-2" />
                Carte
              </TabsTrigger>
              <TabsTrigger value="transfer" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
                <Landmark className="w-4 h-4 mr-2" />
                Virement
              </TabsTrigger>
              <TabsTrigger value="sepa" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
                <Building2 className="w-4 h-4 mr-2" />
                SEPA B2B
              </TabsTrigger>
            </TabsList>

            {/* Card Payment Tab */}
            <TabsContent value="card" className="mt-4">
              <div className="grid sm:grid-cols-2 gap-3">
                {packages.map((pkg) => (
                  <div 
                    key={pkg.id}
                    className={`relative p-4 rounded-xl border transition-all cursor-pointer hover:scale-[1.01] ${
                      selectedPackage?.id === pkg.id
                        ? 'bg-[#D9B35A]/20 border-[#D9B35A]'
                        : pkg.popular 
                          ? 'bg-[#D9B35A]/5 border-[#D9B35A]/30' 
                          : 'bg-white/[0.02] border-white/[0.08] hover:border-white/20'
                    }`}
                    onClick={() => setSelectedPackage(pkg)}
                    data-testid={`package-${pkg.id}`}
                  >
                    {pkg.popular && (
                      <Badge className="absolute -top-2 right-2 bg-[#D9B35A] text-black text-xs">
                        <Sparkles className="w-3 h-3 mr-1" />Populaire
                      </Badge>
                    )}
                    <h4 className="font-semibold text-white/90">{pkg.name}</h4>
                    <p className="text-xs text-white/50 mb-2">{pkg.description}</p>
                    <div className="flex items-end justify-between">
                      <span className="text-xl font-bold text-[#D9B35A]">{pkg.credits} <span className="text-sm font-normal text-white/40">crédits</span></span>
                      <span className="text-lg font-semibold">{pkg.price}€</span>
                    </div>
                  </div>
                ))}
              </div>
              <Button 
                onClick={() => selectedPackage && handleCardPayment(selectedPackage)}
                disabled={!selectedPackage || checkoutLoading}
                className="w-full mt-4 bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
              >
                {checkoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />}
                Payer par carte {selectedPackage && `(${selectedPackage.price}€)`}
              </Button>
              <p className="text-xs text-center text-white/40 mt-2">
                <Lock className="w-3 h-3 inline mr-1" />Paiement sécurisé par Stripe
              </p>
            </TabsContent>

            {/* Bank Transfer Tab */}
            <TabsContent value="transfer" className="mt-4">
              {!transferReference ? (
                <>
                  <div className="mb-4">
                    <Label className="text-white/70">Nom de l'entreprise (pour la référence)</Label>
                    <Input 
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="Ex: Ma Société SAS"
                      className="mt-1 bg-white/[0.04] border-white/10"
                    />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {packages.map((pkg) => (
                      <div 
                        key={pkg.id}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          selectedPackage?.id === pkg.id
                            ? 'bg-[#D9B35A]/20 border-[#D9B35A]'
                            : 'bg-white/[0.02] border-white/[0.08] hover:border-white/20'
                        }`}
                        onClick={() => setSelectedPackage(pkg)}
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{pkg.name}</span>
                          <span className="text-[#D9B35A] font-bold">{pkg.price}€</span>
                        </div>
                        <p className="text-xs text-white/50">{pkg.credits} crédits</p>
                      </div>
                    ))}
                  </div>
                  <Button 
                    onClick={() => selectedPackage && handleBankTransfer(selectedPackage)}
                    disabled={!selectedPackage || !companyName.trim() || checkoutLoading}
                    className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
                  >
                    {checkoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileText className="w-4 h-4 mr-2" />}
                    Générer référence de virement
                  </Button>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-5 h-5 text-green-400" />
                      <span className="font-semibold text-green-400">Référence générée</span>
                    </div>
                    <p className="text-sm text-white/70">Effectuez le virement avec les informations ci-dessous</p>
                  </div>
                  
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-white/60 text-sm">Montant</span>
                      <span className="font-bold text-xl text-[#D9B35A]">{transferReference.amount}€</span>
                    </div>
                    
                    <div className="pt-3 border-t border-white/[0.08]">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-white/60 text-sm">Référence à indiquer</span>
                        <Button variant="ghost" size="sm" onClick={() => copyToClipboard(transferReference.reference, 'ref')} className="h-6 px-2">
                          {copiedField === 'ref' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        </Button>
                      </div>
                      <code className="block p-2 rounded bg-black/30 text-[#D9B35A] text-sm font-mono">{transferReference.reference}</code>
                    </div>
                    
                    <div className="pt-3 border-t border-white/[0.08] space-y-2">
                      <p className="text-white/60 text-sm font-medium">Coordonnées bancaires</p>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-white/50">Bénéficiaire</span>
                        <span className="text-sm">{bankDetails?.account_holder}</span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-white/50">IBAN</span>
                        <div className="flex items-center gap-1">
                          <code className="text-sm font-mono">{bankDetails?.iban}</code>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(bankDetails?.iban?.replace(/\s/g, ''), 'iban')} className="h-5 w-5 p-0">
                            {copiedField === 'iban' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          </Button>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-white/50">BIC</span>
                        <div className="flex items-center gap-1">
                          <code className="text-sm font-mono">{bankDetails?.bic}</code>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(bankDetails?.bic, 'bic')} className="h-5 w-5 p-0">
                            {copiedField === 'bic' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          </Button>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-white/50">Banque</span>
                        <span className="text-sm">{bankDetails?.bank_name} - {bankDetails?.branch}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <p className="text-xs text-amber-400">
                      <AlertCircle className="w-3 h-3 inline mr-1" />
                      Vos crédits seront ajoutés après validation du virement (1-3 jours ouvrés)
                    </p>
                  </div>
                </div>
              )}
            </TabsContent>

            {/* SEPA Direct Debit Tab */}
            <TabsContent value="sepa" className="mt-4">
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <p className="text-xs text-blue-400">
                    <Building2 className="w-3 h-3 inline mr-1" />
                    Le prélèvement SEPA B2B permet des paiements récurrents automatiques
                  </p>
                </div>
                
                <div className="grid gap-3">
                  <div>
                    <Label className="text-white/70">IBAN</Label>
                    <Input 
                      value={sepaIban}
                      onChange={(e) => setSepaIban(e.target.value.toUpperCase())}
                      placeholder="FR76 XXXX XXXX XXXX XXXX XXXX XXX"
                      className="mt-1 bg-white/[0.04] border-white/10 font-mono"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70">Titulaire du compte</Label>
                    <Input 
                      value={sepaName}
                      onChange={(e) => setSepaName(e.target.value)}
                      placeholder="Nom de l'entreprise ou du titulaire"
                      className="mt-1 bg-white/[0.04] border-white/10"
                    />
                  </div>
                  <div>
                    <Label className="text-white/70">Email (pour le mandat)</Label>
                    <Input 
                      type="email"
                      value={sepaEmail}
                      onChange={(e) => setSepaEmail(e.target.value)}
                      placeholder="comptabilite@entreprise.fr"
                      className="mt-1 bg-white/[0.04] border-white/10"
                    />
                  </div>
                </div>
                
                <div className="grid sm:grid-cols-2 gap-3">
                  {packages.map((pkg) => (
                    <div 
                      key={pkg.id}
                      className={`p-3 rounded-xl border cursor-pointer transition-all ${
                        selectedPackage?.id === pkg.id
                          ? 'bg-[#D9B35A]/20 border-[#D9B35A]'
                          : 'bg-white/[0.02] border-white/[0.08] hover:border-white/20'
                      }`}
                      onClick={() => setSelectedPackage(pkg)}
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">{pkg.name}</span>
                        <span className="text-[#D9B35A] font-bold">{pkg.price}€</span>
                      </div>
                      <p className="text-xs text-white/50">{pkg.credits} crédits</p>
                    </div>
                  ))}
                </div>
                
                <Button 
                  onClick={() => selectedPackage && handleSepaSetup(selectedPackage)}
                  disabled={!selectedPackage || !sepaIban || !sepaName || !sepaEmail || sepaLoading}
                  className="w-full bg-purple-600 hover:bg-purple-700"
                >
                  {sepaLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Building2 className="w-4 h-4 mr-2" />}
                  Configurer le prélèvement SEPA
                </Button>
                
                <p className="text-xs text-center text-white/40">
                  En continuant, vous autorisez O'SCOP à débiter votre compte via SEPA
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </div>
  );
}
