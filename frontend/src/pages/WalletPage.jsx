import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, AlertCircle, Loader2, RefreshCw, ShoppingCart } from 'lucide-react';

import { Button } from '../components/ui/button';
import { partners } from '../data/mock';
import { authAPI, walletAPIV2, zonesAPIV2, paymentAPI } from '../services/api';
import { formatCredits } from '../components/wallet/walletUtils';
import { WalletOrgTabs } from '../components/wallet/WalletOrgTabs';
import { TopupDialog, ZoneAddDialog } from '../components/wallet/WalletDialogs';
import { BuyCreditsDialog } from '../components/wallet/BuyCreditsDialog';

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
      toast.error(i18n.t('wallet.toast_verif_expiree'));
      navigate('/wallet', { replace: true });
      return;
    }

    try {
      const status = await paymentAPI.getStatus(sessionId);

      if (status.payment_status === 'paid' && status.credited) {
        setPaymentChecking(false);
        toast.success(i18n.t('wallet.toast_credits_ajoutes', { count: status.credits }));
        navigate('/wallet', { replace: true });
        const userData = await authAPI.getMe();
        setUser(userData);
        return;
      } else if (status.status === 'EXPIRED') {
        setPaymentChecking(false);
        toast.error(i18n.t('wallet.toast_session_expiree'));
        navigate('/wallet', { replace: true });
        return;
      }

      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Payment status error:', error);
      setPaymentChecking(false);
      toast.error(i18n.t('wallet.toast_erreur_verif'));
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
      toast.error(i18n.t('wallet.toast_annule'));
      navigate('/wallet', { replace: true });
    }
  }, [searchParams, navigate, pollPaymentStatus]);

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
    toast.success(i18n.t('wallet.toast_copie'));
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

        const packagesData = await paymentAPI.getPackages().catch(() => ({ packages: [] }));
        setPackages(packagesData.packages || []);

        const orgIdValue = userData.org_id || userData.organization_id;
        if (orgIdValue) {
          setOrgId(orgIdValue);

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

  const refreshWallet = async () => {
    if (!orgId) return;
    try {
      const [walletData, ledgerData] = await Promise.all([
        walletAPIV2.get(orgId),
        walletAPIV2.getLedger(orgId, 50),
      ]);
      setWallet(walletData);
      setLedger(ledgerData);
      toast.success(i18n.t('wallet.toast_actualise'));
    } catch (error) {
      toast.error('Erreur lors de l\'actualisation');
    }
  };

  const handleCardPayment = async (pkg) => {
    setSelectedPackage(pkg);
    setCheckoutLoading(true);

    try {
      const response = await paymentAPI.createCheckout(pkg.id);
      window.location.href = response.checkout_url;
    } catch (error) {
      toast.error(error.message || i18n.t('wallet.toast_erreur_paiement'));
      setCheckoutLoading(false);
    }
  };

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
      toast.success(i18n.t('wallet.toast_virement'));
    } catch (error) {
      toast.error(error.message || i18n.t('wallet.toast_erreur_virement'));
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleSepaSetup = async (pkg) => {
    if (!sepaIban.trim() || !sepaName.trim() || !sepaEmail.trim()) {
      toast.error('Veuillez remplir tous les champs SEPA');
      return;
    }

    setSelectedPackage(pkg);
    setSepaLoading(true);

    try {
      const response = await paymentAPI.createSepaSetup(pkg.id, sepaIban, sepaName, sepaEmail);
      toast.success(i18n.t('wallet.toast_sepa'));

      const confirmResponse = await paymentAPI.confirmSepaPayment(response.setup_id);
      if (confirmResponse.status === 'succeeded') {
        toast.success(i18n.t('wallet.toast_credits_courts', { count: confirmResponse.credits }));
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

  const openBuyCredits = async () => {
    setBuyCreditsOpen(true);
    setTransferReference(null);
    if (!bankDetails) {
      try {
        const details = await paymentAPI.getBankDetails();
        setBankDetails(details.bank_details);
      } catch (e) {
        console.error('Failed to load bank details:', e);
      }
    }
  };

  const handleTopup = async () => {
    if (!orgId || topupAmount < 10) {
      toast.error(i18n.t('wallet.toast_montant_min'));
      return;
    }

    setTopupLoading(true);
    try {
      await walletAPIV2.topup(orgId, topupAmount);
      toast.success(i18n.t('wallet.toast_credits_ajoutes_2', { count: topupAmount }));
      setTopupOpen(false);
      setTopupAmount(100);
      refreshWallet();
    } catch (error) {
      toast.error(error.message || 'Erreur lors de la recharge');
    } finally {
      setTopupLoading(false);
    }
  };

  const handleAddZone = async () => {
    if (!orgId || !selectedZone) return;

    setZoneLoading(true);
    try {
      await zonesAPIV2.addEntitlement(orgId, selectedZone.id);
      toast.success(i18n.t('wallet.toast_zone', { name: selectedZone.name }));
      setZoneDialogOpen(false);
      setSelectedZone(null);

      const entitlementsData = await zonesAPIV2.getOrgEntitlements(orgId);
      setEntitledZones(entitlementsData);
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'activation');
    } finally {
      setZoneLoading(false);
    }
  };

  const availableZones = allZones.filter(z =>
    !entitledZones.some(e => e.zone_id === z.id)
  );

  if (loading || paymentChecking) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
        {paymentChecking && (
          <p className="text-white/60 text-sm">{i18n.t('wallet.verification_du_paiement_en')}</p>
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
                {formatCredits(user.credits || 0)} {i18n.t('wallet.credits')}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={refreshWallet} className="h-6 w-6 p-0 hover:bg-white/10">
              <RefreshCw className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-4">
        <div className="mb-4">
          <h1 className="text-2xl font-bold mb-1">{i18n.t('wallet.wallet_credits')}</h1>
          <p className="text-white/60 text-sm">{i18n.t('wallet.gerez_vos_credits_et')}</p>
        </div>

        {/* User Credits Card (always visible) */}
        <div className="mb-6 glass-panel-soft rounded-[18px] p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white/60 mb-1">{i18n.t('wallet.vos_credits_personnels')}</p>
              <p className="text-3xl font-bold text-[#D9B35A]">
                {formatCredits(user?.credits || 0)}
                <span className="text-base font-normal text-white/50 ml-2">{i18n.t('wallet.credits')}</span>
              </p>
            </div>
            <Button
              onClick={openBuyCredits}
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
              data-testid="buy-credits-btn"
            >
              <ShoppingCart className="w-4 h-4 mr-2" />
              {i18n.t('wallet.acheter_des_credits')}
            </Button>
          </div>
        </div>

        {/* No org info */}
        {!orgId && (
          <div className="mb-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-blue-400">{i18n.t('wallet.organisation_b2b')}</p>
                <p className="text-sm text-blue-400/80">
                  {i18n.t('wallet.pour_acceder_au_wallet')}
                </p>
                <Link to="/onboarding" className="text-sm text-blue-400 underline mt-2 inline-block">
                  {i18n.t('wallet.demander_l_adhesion')}
                </Link>
              </div>
            </div>
          </div>
        )}

        {orgId && (
          <WalletOrgTabs
            wallet={wallet}
            ledger={ledger}
            allZones={allZones}
            entitledZones={entitledZones}
            availableZones={availableZones}
            onTopupOpen={() => setTopupOpen(true)}
            onOpenZoneDialog={() => setZoneDialogOpen(true)}
            onZoneClick={(zone) => {
              setSelectedZone(zone);
              setZoneDialogOpen(true);
            }}
          />
        )}
      </div>

      <TopupDialog
        open={topupOpen}
        onOpenChange={setTopupOpen}
        amount={topupAmount}
        setAmount={setTopupAmount}
        loading={topupLoading}
        onSubmit={handleTopup}
      />

      <ZoneAddDialog
        open={zoneDialogOpen}
        onOpenChange={setZoneDialogOpen}
        selectedZone={selectedZone}
        loading={zoneLoading}
        onSubmit={handleAddZone}
        onCancel={() => {
          setZoneDialogOpen(false);
          setSelectedZone(null);
        }}
      />

      <BuyCreditsDialog
        open={buyCreditsOpen}
        onOpenChange={(open) => {
          setBuyCreditsOpen(open);
          if (!open) {
            setTransferReference(null);
            setSelectedPackage(null);
            setPaymentMethod('card');
          }
        }}
        packages={packages}
        selectedPackage={selectedPackage}
        setSelectedPackage={setSelectedPackage}
        paymentMethod={paymentMethod}
        setPaymentMethod={setPaymentMethod}
        checkoutLoading={checkoutLoading}
        onCardPayment={handleCardPayment}
        companyName={companyName}
        setCompanyName={setCompanyName}
        onBankTransfer={handleBankTransfer}
        transferReference={transferReference}
        bankDetails={bankDetails}
        copiedField={copiedField}
        copyToClipboard={copyToClipboard}
        sepaIban={sepaIban}
        setSepaIban={setSepaIban}
        sepaName={sepaName}
        setSepaName={setSepaName}
        sepaEmail={sepaEmail}
        setSepaEmail={setSepaEmail}
        sepaLoading={sepaLoading}
        onSepaSetup={handleSepaSetup}
      />
    </div>
  );
}
