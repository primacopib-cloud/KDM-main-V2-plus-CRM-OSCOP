import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Ticket, Wallet, Sparkles, ShoppingBag, Clock,
  RefreshCw, Plus, ArrowDownRight, ArrowUpRight, AlertTriangle,
  CheckCircle2, ArrowRight, Zap,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import StripeCheckoutButton from '../components/StripeCheckoutButton';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Label } from '../components/ui/label';
import { lolodriveAPI, authAPI } from '../services/api';
import PreselectedRelayBadge from '../components/PreselectedRelayBadge';
import { toast } from 'sonner';

export default function PassSpacePage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [savings, setSavings] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [referral, setReferral] = useState(null);
  const [claimCode, setClaimCode] = useState('');
  const [autoRenewBusy, setAutoRenewBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [rechargeOpen, setRechargeOpen] = useState(false);
  const [selectedPack, setSelectedPack] = useState('STANDARD');
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    if (!authAPI.isAuthenticated()) {
      navigate('/connexion');
      return;
    }
    load();
  }, [navigate]);

  const load = async () => {
    try {
      setLoading(true);
      const [pass, wallet, o, sv, ref] = await Promise.all([
        lolodriveAPI.myPass(),
        lolodriveAPI.myWallet(),
        lolodriveAPI.myOrders(),
        lolodriveAPI.mySavings().catch(() => null),
        lolodriveAPI.getMyReferralCode().catch(() => null),
      ]);
      setData({ ...pass, wallet: wallet.wallet });
      setLedger(wallet.ledger || []);
      setOrders(o.orders || []);
      setSavings(sv);
      setReferral(ref);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const activatePassDemo = async () => {
    setActivating(true);
    try {
      const r = await lolodriveAPI.simulatePassActivation();
      toast.success(`PASS activé ! ${r.uc_granted} UC crédités. Valable jusqu'au ${new Date(r.ends_at).toLocaleDateString('fr-FR')}.`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActivating(false);
    }
  };

  const recharge = async () => {
    try {
      const r = await lolodriveAPI.checkoutRecharge(window.location.origin, selectedPack);
      if (r?.url) {
        window.location.href = r.url;
      } else {
        toast.error('Erreur Stripe');
      }
    } catch (e) {
      toast.error(e.message);
    }
  };

  const remainingDays = () => {
    if (!data?.pass?.ends_at) return 0;
    return Math.max(0, Math.ceil((new Date(data.pass.ends_at) - new Date()) / (1000 * 60 * 60 * 24)));
  };

  const toggleAutoRenew = async () => {
    if (!data?.pass) return;
    setAutoRenewBusy(true);
    try {
      const r = await lolodriveAPI.setPassAutoRenew(!data.pass.is_auto_renew);
      toast.success(r.is_auto_renew ? 'Renouvellement automatique activé' : 'Renouvellement automatique désactivé');
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setAutoRenewBusy(false);
    }
  };

  const claimReferral = async () => {
    if (!claimCode.trim()) return;
    try {
      const r = await lolodriveAPI.claimReferralCode(claimCode.trim());
      toast.success(`Code accepté ! ${r.bonus_uc_each} UC crédités sur votre wallet.`);
      setClaimCode('');
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const copyReferral = () => {
    if (!referral?.code) return;
    navigator.clipboard.writeText(referral.code).then(
      () => toast.success(`Code ${referral.code} copié`),
      () => toast.error('Copie impossible')
    );
  };

  const days = remainingDays();
  const expirationLevel = days <= 3 ? 'critical' : days <= 7 ? 'warning' : 'ok';

  return (
    <LolodriveLayout
      title="Mon Espace PASS"
      subtitle="PASS Vie Chère, wallet UC, mes commandes et économies réalisées."
      actions={
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
        </Button>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}
      {!loading && data && (
        <>
          <PreselectedRelayBadge testId="pass-preselected-relay" className="mb-4" />
          {/* Hero PASS state */}
          <SectionCard className="mb-6 relative overflow-hidden">
            <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full blur-3xl opacity-30"
              style={{ background: data.active ? '#D9B35A' : '#666' }} />
            {data.active ? (
              <div className="relative flex flex-wrap gap-6 items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge color="#D9B35A">PASS Vie Chère actif</Badge>
                    {expirationLevel === 'critical' && (
                      <Badge color="#ef4444">
                        <AlertTriangle className="w-3 h-3 mr-1 inline" />
                        Expire bientôt
                      </Badge>
                    )}
                  </div>
                  <div className="mt-3 text-5xl font-bold tracking-tight">
                    {data.wallet.balance_uc}
                    <span className="text-base text-white/40 font-normal ml-2">UC disponibles</span>
                  </div>
                  <div className="text-sm mt-2 flex items-center gap-3 flex-wrap">
                    <span className={
                      expirationLevel === 'critical' ? 'text-red-400 font-semibold' :
                      expirationLevel === 'warning' ? 'text-amber-400 font-semibold' :
                      'text-white/50'
                    }>
                      <Clock className="w-3 h-3 inline mr-1" />
                      Expire dans {days} jours
                    </span>
                    <span className="text-white/40">
                      ({new Date(data.pass.ends_at).toLocaleDateString('fr-FR')})
                    </span>
                  </div>
                  <div className="text-xs text-white/40 mt-2 max-w-md">
                    {data.pass.is_auto_renew ? (
                      <>Renouvellement automatique <strong className="text-emerald-400">activé</strong>. À l'expiration, un nouveau PASS sera proposé.</>
                    ) : (
                      <>Pas de renouvellement automatique. À l'expiration, votre PASS sera désactivé. Les UC non utilisés ne sont pas remboursables (unité d'usage interne).</>
                    )}
                  </div>
                  <div className="mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={toggleAutoRenew}
                      disabled={autoRenewBusy}
                      data-testid="toggle-auto-renew-btn"
                      className="text-xs"
                    >
                      <RefreshCw className="w-3 h-3 mr-1.5" />
                      {data.pass.is_auto_renew ? 'Désactiver le renouvellement auto' : 'Activer le renouvellement auto'}
                    </Button>
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button asChild variant="outline" data-testid="goto-catalogue-btn">
                    <Link to="/catalogue-lolodrive">
                      <ShoppingBag className="w-4 h-4 mr-2" /> Voir le catalogue
                    </Link>
                  </Button>
                  <Dialog open={rechargeOpen} onOpenChange={setRechargeOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="open-recharge-btn"
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        <Plus className="w-4 h-4 mr-2" /> Recharger UC
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-[#15151c] border-white/10 text-white">
                      <DialogHeader>
                        <DialogTitle>Recharger mon wallet UC</DialogTitle>
                      </DialogHeader>
                      <p className="text-xs text-white/50 mb-2">
                        Le wallet UC est rechargeable uniquement si votre PASS est actif. Aucun renouvellement automatique.
                      </p>
                      <RadioGroup value={selectedPack} onValueChange={setSelectedPack} className="space-y-2">
                        {[
                          { id: 'MINI', label: 'Mini', amount: '20 €', uc: '200 UC' },
                          { id: 'STANDARD', label: 'Standard', amount: '40 €', uc: '400 UC' },
                          { id: 'MAXI', label: 'Maxi', amount: '70 €', uc: '720 UC ✨', bonus: true },
                        ].map((p) => (
                          <label
                            key={p.id}
                            htmlFor={`pack-${p.id}`}
                            className="flex items-center gap-3 p-3 rounded-lg border border-white/10 hover:border-[#D9B35A]/40 cursor-pointer"
                            data-testid={`pack-${p.id}`}
                          >
                            <RadioGroupItem id={`pack-${p.id}`} value={p.id} />
                            <div className="flex-1">
                              <div className="font-medium flex items-center gap-2">
                                {p.label}
                                {p.bonus && <Badge color="#D9B35A">Bonus +20 UC</Badge>}
                              </div>
                              <div className="text-xs text-white/40">{p.amount} → {p.uc}</div>
                            </div>
                          </label>
                        ))}
                      </RadioGroup>
                      <Button onClick={recharge} data-testid="confirm-recharge-btn"
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        Payer par CB (Stripe Checkout)
                      </Button>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
            ) : (
              <div className="relative">
                <Badge color="#666">PASS inactif</Badge>
                <h2 className="text-2xl font-bold mt-3">Activez votre PASS Vie Chère</h2>
                <p className="text-sm text-white/60 mt-1 mb-4 max-w-2xl">
                  <strong>60 € = 600 UC</strong>, valable 30 jours. Accès aux prix PASS sur les produits ESSENTIELS,
                  paiement en UC sur l'ensemble du catalogue. Sans renouvellement automatique : vous restez maître de votre engagement.
                </p>
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={activatePassDemo} size="lg" disabled={activating} data-testid="activate-pass-demo-btn"
                    style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                    <Zap className="w-4 h-4 mr-2" />
                    {activating ? 'Activation...' : 'Activer mon PASS (mode démo)'}
                  </Button>
                  <StripeCheckoutButton
                    createSession={(origin) => lolodriveAPI.checkoutPass(origin)}
                    label="Payer 60 € par CB (Stripe)"
                    variant="outline"
                    size="lg"
                    testId="activate-pass-stripe-btn"
                    icon={<ShoppingBag className="w-4 h-4 mr-2" />}
                  />
                </div>
                <p className="text-[11px] text-white/30 mt-3">
                  Mode démo : active le PASS sans paiement réel. Stripe (test) ouvre un formulaire CB hosted page.
                </p>
              </div>
            )}
          </SectionCard>

          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-balance" label="Solde UC" value={data.wallet.balance_uc} icon={Wallet} accent="#D9B35A" />
            <KpiCard
              testId="kpi-savings"
              label="Économies réalisées"
              value={fmtEUR(savings?.savings_cents || 0)}
              sub={savings ? `sur ${savings.essential_items} produit(s) essentiel(s)` : ''}
              icon={Sparkles}
              accent="#10b981"
            />
            <KpiCard testId="kpi-orders" label="Mes commandes" value={orders.length} sub={`${orders.filter(o => o.status === 'FULFILLED').length} retirée(s)`} icon={ShoppingBag} accent="#7c3aed" />
            <KpiCard
              testId="kpi-status"
              label="Statut PASS"
              value={data.active ? 'ACTIF' : 'INACTIF'}
              sub={data.active ? `${days}j restants` : 'Activez pour économiser'}
              icon={Ticket}
              accent={data.active ? (expirationLevel === 'critical' ? '#ef4444' : '#10b981') : '#666'}
            />
          </div>

          {/* Wallet ledger */}
          <SectionCard
            title="Historique du wallet UC"
            action={<span className="text-xs text-white/40">{ledger.length} mouvement(s)</span>}
            className="mb-6"
          >
            {ledger.length === 0 && (
              <div className="text-sm text-white/40 py-4 text-center">
                Aucun mouvement encore. Activez votre PASS pour commencer.
              </div>
            )}
            <div className="space-y-2">
              {ledger.slice(0, 8).map((l) => (
                <div key={l.id} data-testid={`ledger-${l.id}`}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                      style={{ background: l.type === 'CREDIT' ? '#10b98120' : '#ef444420' }}>
                      {l.type === 'CREDIT'
                        ? <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                        : <ArrowDownRight className="w-4 h-4 text-red-400" />}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{reasonLabel(l.reason)}</div>
                      <div className="text-xs text-white/40">
                        {new Date(l.created_at).toLocaleString('fr-FR')}
                      </div>
                    </div>
                  </div>
                  <div className={`font-bold text-sm ${l.type === 'CREDIT' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {l.type === 'CREDIT' ? '+' : '-'}{l.amount_uc} UC
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Orders */}
          <SectionCard
            title="Mes commandes récentes"
            action={
              <Link to="/catalogue-lolodrive" className="text-xs text-[#D9B35A] hover:underline flex items-center gap-1" data-testid="goto-catalogue-link">
                + Nouvelle commande <ArrowRight className="w-3 h-3" />
              </Link>
            }
          >
            {orders.length === 0 && (
              <div className="text-sm text-white/40 py-8 text-center">
                Aucune commande pour le moment.
                <div className="mt-2">
                  <Button asChild size="sm" variant="outline">
                    <Link to="/catalogue-lolodrive">Découvrir le catalogue</Link>
                  </Button>
                </div>
              </div>
            )}
            <div className="space-y-2">
              {orders.slice(0, 8).map((o) => (
                <div key={o.id} data-testid={`order-${o.id}`}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#7c3aed]/20 shrink-0">
                      <ShoppingBag className="w-4 h-4 text-[#a78bfa]" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-medium font-mono truncate">{o.order_number}</div>
                      <div className="text-xs text-white/40">
                        {o.fulfillment_type} · {o.items?.length || 0} article(s) ·{' '}
                        {new Date(o.created_at).toLocaleDateString('fr-FR')}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-bold text-sm">{fmtEUR(o.total_cents)}</div>
                    <div className="flex gap-1 justify-end mt-0.5">
                      {o.pay_with_uc && <Badge color="#D9B35A">UC</Badge>}
                      <Badge color={statusColor(o.status)}>{o.status}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Parrainage coopérateur */}
          {referral && (
            <SectionCard
              title="Parrainage coopérateur"
              action={<Badge color="#7c3aed">+{referral.bonus_uc_per_use} UC parrain & filleul</Badge>}
              data-testid="referral-section"
            >
              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-lg p-4 bg-[#7c3aed]/[0.08] border border-[#7c3aed]/30">
                  <div className="text-xs text-white/50 mb-1">Mon code</div>
                  <div className="flex items-center gap-2 mb-2">
                    <code data-testid="referral-code" className="text-lg font-mono font-bold text-[#a78bfa] tracking-wider">{referral.code}</code>
                    <Button size="sm" variant="outline" onClick={copyReferral} data-testid="copy-referral-btn" className="text-xs h-7">Copier</Button>
                  </div>
                  <div className="text-xs text-white/50">
                    Utilisations : <strong>{referral.uses}/{referral.max_uses}</strong> — chaque filleul vous fait gagner <strong>{referral.bonus_uc_per_use} UC</strong>.
                  </div>
                </div>
                <div className="rounded-lg p-4 bg-white/[0.03] border border-white/[0.08]">
                  <div className="text-xs text-white/50 mb-1">J'ai un code de parrainage</div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={claimCode}
                      onChange={(e) => setClaimCode(e.target.value.toUpperCase())}
                      placeholder="KDM-XXXXXX"
                      data-testid="claim-code-input"
                      className="flex-1 px-3 py-2 text-sm bg-white/[0.04] border border-white/10 rounded-md font-mono uppercase"
                    />
                    <Button onClick={claimReferral} data-testid="claim-referral-btn"
                      style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                      Activer
                    </Button>
                  </div>
                  <div className="text-[11px] text-white/40 mt-2">
                    Limite : un code par compte. Vous recevez {referral.bonus_uc_per_use} UC dès activation.
                  </div>
                </div>
              </div>
            </SectionCard>
          )}
        </>
      )}
    </LolodriveLayout>
  );
}

const reasonLabel = (r) => ({
  PASS_ACTIVATION: 'Activation PASS',
  PASS_ACTIVATION_DEMO: 'Activation PASS (démo)',
  RECHARGE: 'Recharge wallet',
  ORDER_PAY_UC: 'Paiement commande en UC',
}[r] || r);

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  if (s === 'CANCELLED' || s === 'REFUNDED') return '#ef4444';
  return '#7c3aed';
};
