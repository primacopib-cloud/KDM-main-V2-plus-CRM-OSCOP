import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Ticket, Wallet, Sparkles, ShoppingBag, Clock, CheckCircle2,
  RefreshCw, Plus, ArrowDownRight, ArrowUpRight, Zap,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Label } from '../components/ui/label';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';

export default function PassSpacePage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rechargeOpen, setRechargeOpen] = useState(false);
  const [selectedPack, setSelectedPack] = useState('STANDARD');

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
      const [pass, wallet, o, c] = await Promise.all([
        lolodriveAPI.myPass(),
        lolodriveAPI.myWallet(),
        lolodriveAPI.myOrders(),
        lolodriveAPI.catalogProducts(),
      ]);
      setData({ ...pass, wallet: wallet.wallet });
      setLedger(wallet.ledger || []);
      setOrders(o.orders || []);
      setProducts(c.products || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const activatePass = async () => {
    try {
      const r = await lolodriveAPI.passIntent();
      toast.success('PaymentIntent PASS créé. (Démo Stripe test)');
      // For demo: simulate webhook by waiting 1.5s
      toast.info('En production : redirection Stripe Elements pour saisie CB.');
      console.log('client_secret:', r.client_secret);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const recharge = async () => {
    try {
      const r = await lolodriveAPI.rechargeIntent(selectedPack);
      toast.success(`Recharge ${selectedPack} initiée. Client secret généré.`);
      setRechargeOpen(false);
      console.log('client_secret:', r.client_secret);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const remainingDays = () => {
    if (!data?.pass?.ends_at) return 0;
    return Math.max(0, Math.ceil((new Date(data.pass.ends_at) - new Date()) / (1000 * 60 * 60 * 24)));
  };

  return (
    <LolodriveLayout
      title="Mon Espace PASS"
      subtitle="Pass Vie Chère, wallet UC, mes commandes et activité."
      actions={
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
        </Button>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}
      {!loading && data && (
        <>
          {/* PASS state */}
          <SectionCard className="mb-6 relative overflow-hidden">
            <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full blur-3xl opacity-30"
              style={{ background: data.active ? '#D9B35A' : '#666' }} />
            {data.active ? (
              <div className="relative flex flex-wrap gap-6 items-start justify-between">
                <div>
                  <Badge color="#D9B35A">PASS Vie Chère actif</Badge>
                  <div className="mt-3 text-4xl font-bold tracking-tight">
                    {data.wallet.balance_uc} <span className="text-base text-white/40 font-normal">UC</span>
                  </div>
                  <div className="text-sm text-white/50 mt-1">
                    Expire dans <span className="text-[#D9B35A] font-medium">{remainingDays()} jours</span> ·{' '}
                    {new Date(data.pass.ends_at).toLocaleDateString('fr-FR')}
                  </div>
                  <div className="text-xs text-white/40 mt-2">
                    Pas de renouvellement automatique. Vous serez notifié avant expiration.
                  </div>
                </div>
                <div className="flex gap-2">
                  <Dialog open={rechargeOpen} onOpenChange={setRechargeOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="open-recharge-btn"
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        <Plus className="w-4 h-4 mr-2" /> Recharger UC
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-[#15151c] border-white/10 text-white">
                      <DialogHeader>
                        <DialogTitle>Choisir un pack UC</DialogTitle>
                      </DialogHeader>
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
                                {p.bonus && <Badge color="#D9B35A">Bonus</Badge>}
                              </div>
                              <div className="text-xs text-white/40">{p.amount} → {p.uc}</div>
                            </div>
                          </label>
                        ))}
                      </RadioGroup>
                      <Button onClick={recharge} data-testid="confirm-recharge-btn"
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        Payer par CB (Stripe test)
                      </Button>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
            ) : (
              <div className="relative">
                <Badge color="#666">PASS inactif</Badge>
                <h2 className="text-2xl font-bold mt-3">Activez votre PASS Vie Chère</h2>
                <p className="text-sm text-white/60 mt-1 mb-4">
                  60 € = 600 UC, valable 30 jours. Accès aux prix PASS sur les produits ESSENTIELS.
                  Sans renouvellement automatique.
                </p>
                <Button onClick={activatePass} size="lg" data-testid="activate-pass-btn"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                  <Ticket className="w-4 h-4 mr-2" /> Activer mon PASS pour 60 €
                </Button>
              </div>
            )}
          </SectionCard>

          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-balance" label="Solde UC" value={data.wallet.balance_uc} icon={Wallet} accent="#D9B35A" />
            <KpiCard testId="kpi-orders" label="Mes commandes" value={orders.length} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-essentials" label="Produits ESSENTIELS" value={products.filter(p => p.catalog_type === 'ESSENTIAL').length} icon={Sparkles} accent="#7c3aed" />
            <KpiCard testId="kpi-savings" label="Statut PASS" value={data.active ? 'ACTIF' : 'INACTIF'} sub={data.active ? `${remainingDays()}j restants` : 'Activez pour économiser'} icon={Ticket} accent={data.active ? '#10b981' : '#ef4444'} />
          </div>

          {/* Wallet ledger */}
          <SectionCard title="Historique du wallet" className="mb-6">
            {ledger.length === 0 && (
              <div className="text-sm text-white/40 py-4 text-center">Aucun mouvement encore.</div>
            )}
            <div className="space-y-2">
              {ledger.map((l) => (
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
                      <div className="text-sm font-medium">{l.reason}</div>
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
          <SectionCard title="Mes commandes récentes"
            action={<Link to="/catalogue-lolodrive" className="text-xs text-[#D9B35A] hover:underline">+ Nouvelle commande</Link>}>
            {orders.length === 0 && (
              <div className="text-sm text-white/40 py-4 text-center">Aucune commande pour le moment.</div>
            )}
            <div className="space-y-2">
              {orders.slice(0, 8).map((o) => (
                <div key={o.id} data-testid={`order-${o.id}`}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#7c3aed]/20">
                      <ShoppingBag className="w-4 h-4 text-[#a78bfa]" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{o.order_number}</div>
                      <div className="text-xs text-white/40">
                        {o.fulfillment_type} · {o.items?.length || 0} article(s) ·{' '}
                        {new Date(o.created_at).toLocaleDateString('fr-FR')}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-sm">{fmtEUR(o.total_cents)}</div>
                    <Badge color={statusColor(o.status)}>{o.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        </>
      )}
    </LolodriveLayout>
  );
}

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  if (s === 'CANCELLED' || s === 'REFUNDED') return '#ef4444';
  return '#7c3aed';
};
