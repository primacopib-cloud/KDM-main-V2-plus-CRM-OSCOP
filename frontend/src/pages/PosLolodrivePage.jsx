import React, { useEffect, useRef, useState } from 'react';
import {
  Truck, Package, CheckCircle2, Clock, RefreshCw, ScanLine, AlertCircle,
  Bell, BellOff, User, Calendar, XCircle, Wifi, WifiOff,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { lolodriveAPI, authAPI } from '../services/api';
import useLolodriveWebSocket from '../hooks/useLolodriveWebSocket';
import { toast } from 'sonner';

const STATUS_ORDER = ['PAID', 'PREPARING', 'READY', 'FULFILLED'];
const POLL_INTERVAL_MS = 30000; // fallback polling when WS off

export default function PosLolodrivePage() {
  const [orders, setOrders] = useState([]);
  const [users, setUsers] = useState({});
  const [tab, setTab] = useState('PAID');
  const [pointCode, setPointCode] = useState('');
  const [scanInput, setScanInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [soundOn, setSoundOn] = useState(true);
  const [compact, setCompact] = useState(false);
  const [cancelDialog, setCancelDialog] = useState({ open: false, order: null, reason: '', refundUc: true });
  const previousPaidCountRef = useRef(0);

  const isAdmin = authAPI.getCurrentUser()?.is_admin || ['SUPER_ADMIN', 'ADMIN'].includes(authAPI.getCurrentUser()?.role);

  // WebSocket subscription for real-time POS events
  const { connected: wsConnected } = useLolodriveWebSocket({
    isAdmin: !!isAdmin,
    enabled: autoRefresh,
    onMessage: (msg) => {
      if (msg.type === 'lolodrive_pos_event') {
        const ev = msg.payload?.event;
        if (['order.paid', 'order.status_changed', 'order.fulfilled', 'order.cancelled'].includes(ev)) {
          load({ silent: true });
          if (ev === 'order.paid' && soundOn) {
            toast.success('Nouvelle commande à préparer !', { duration: 4000 });
            playBeep();
          }
        }
      }
    },
  });

  const playBeep = () => {
    if (!soundOn) return;
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = 880;
      o.connect(g);
      g.connect(ctx.destination);
      g.gain.setValueAtTime(0.15, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      o.start();
      o.stop(ctx.currentTime + 0.25);
    } catch {
      // ignore audio errors
    }
  };

  const load = async ({ silent = false } = {}) => {
    try {
      if (!silent) setLoading(true);
      const r = await lolodriveAPI.posOrders(tab !== 'ALL' ? tab : null, pointCode || null);
      const newOrders = r.orders || [];

      // Detect new PAID orders
      if (silent && tab !== 'FULFILLED') {
        const paidNow = newOrders.filter((o) => o.status === 'PAID').length;
        if (paidNow > previousPaidCountRef.current) {
          const delta = paidNow - previousPaidCountRef.current;
          toast.success(`${delta} nouvelle(s) commande(s) à préparer`, { duration: 4000 });
          playBeep();
        }
        previousPaidCountRef.current = paidNow;
      } else {
        previousPaidCountRef.current = newOrders.filter((o) => o.status === 'PAID').length;
      }

      setOrders(newOrders);

      // Fetch user/customer info (cached)
      const userIds = [...new Set(newOrders.map((o) => o.user_id).filter(Boolean))];
      const missing = userIds.filter((uid) => !users[uid]);
      if (missing.length > 0) {
        // Best-effort lookup: we don't have a public /users/{id} so we degrade gracefully
        const newMap = { ...users };
        missing.forEach((uid) => { newMap[uid] = { name: `Client ${uid.slice(0, 8)}` }; });
        setUsers(newMap);
      }
    } catch (e) {
      if (!silent) toast.error(e.message);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-line */ }, [tab, pointCode]);

  // Polling fallback (only when WS not connected)
  useEffect(() => {
    if (!autoRefresh || wsConnected) return;
    const id = setInterval(() => load({ silent: true }), POLL_INTERVAL_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line
  }, [autoRefresh, wsConnected, tab, pointCode]);

  const transitionTo = async (orderId, status) => {
    setActing(orderId);
    try {
      await lolodriveAPI.posUpdateStatus(orderId, status);
      toast.success(`Commande → ${status}`);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActing(null);
    }
  };

  const handleScan = async () => {
    if (!scanInput) return;
    setActing(scanInput);
    try {
      const order = orders.find((o) => o.order_number === scanInput || o.id === scanInput);
      const id = order?.id || scanInput;
      await lolodriveAPI.posScan(id);
      toast.success(`Commande ${scanInput} retirée ✅`);
      setScanInput('');
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActing(null);
    }
  };

  const confirmCancel = async () => {
    if (!cancelDialog.order) return;
    const orderId = cancelDialog.order.id;
    setActing(orderId);
    try {
      const r = await lolodriveAPI.posCancelOrder(orderId, cancelDialog.reason || 'Annulation POS', cancelDialog.refundUc);
      toast.success(`Commande ${r.status === 'REFUNDED' ? 'remboursée en UC' : 'annulée'}`);
      setCancelDialog({ open: false, order: null, reason: '', refundUc: true });
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setActing(null);
    }
  };

  const counts = STATUS_ORDER.reduce((acc, s) => {
    acc[s] = orders.filter((o) => o.status === s).length;
    return acc;
  }, {});
  const toProcess = (counts.PAID || 0) + (counts.PREPARING || 0);

  return (
    <LolodriveLayout
      title="Interface POS LOLODRIVE"
      subtitle="File des commandes, transitions de statut et scan de retrait."
      actions={
        <>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10" data-testid="ws-status">
            {wsConnected ? <Wifi className="w-3 h-3 text-emerald-400" /> : <WifiOff className="w-3 h-3 text-amber-400" />}
            <Label className="text-xs">{wsConnected ? 'Temps réel' : 'Polling'}</Label>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10">
            <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} data-testid="auto-refresh-switch" />
            <Label className="text-xs">Live</Label>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10">
            <Switch checked={soundOn} onCheckedChange={setSoundOn} data-testid="sound-switch" />
            {soundOn ? <Bell className="w-3 h-3" /> : <BellOff className="w-3 h-3" />}
          </div>
          <Button variant="outline" size="sm" onClick={() => load()} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
        </>
      }
    >
      {/* À traiter highlight */}
      {toProcess > 0 && (
        <div className="mb-4 rounded-2xl border border-amber-400/30 bg-amber-400/[0.05] p-4 flex items-center gap-3"
          data-testid="to-process-banner">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="flex-1">
            <div className="font-semibold text-amber-300">{toProcess} commande(s) à traiter</div>
            <div className="text-xs text-white/50">
              {counts.PAID || 0} à préparer · {counts.PREPARING || 0} en préparation
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="grid md:grid-cols-3 gap-3 mb-6">
        <div className="md:col-span-2">
          <Input
            placeholder="Filtrer par code Lolo Point (ex: LP-PAP)"
            value={pointCode}
            onChange={(e) => setPointCode(e.target.value)}
            className="bg-white/[0.04] border-white/10"
            data-testid="point-code-input"
          />
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="N° commande à scanner…"
            value={scanInput}
            onChange={(e) => setScanInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleScan()}
            className="bg-white/[0.04] border-white/10 font-mono"
            data-testid="scan-input"
          />
          <Button onClick={handleScan} data-testid="scan-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <ScanLine className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard testId="kpi-paid" label="Payées" value={counts.PAID || 0} icon={Clock} accent="#3b82f6" />
        <KpiCard testId="kpi-preparing" label="En préparation" value={counts.PREPARING || 0} icon={Package} accent="#7c3aed" />
        <KpiCard testId="kpi-ready" label="Prêtes" value={counts.READY || 0} icon={CheckCircle2} accent="#D9B35A" />
        <KpiCard testId="kpi-fulfilled" label="Retirées" value={counts.FULFILLED || 0} icon={Truck} accent="#10b981" />
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="bg-white/[0.04] border border-white/10">
            {['ALL', ...STATUS_ORDER].map((s) => (
              <TabsTrigger key={s} value={s} data-testid={`tab-${s}`}>
                {s}{counts[s] != null && s !== 'ALL' && ` (${counts[s]})`}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="flex items-center gap-2 text-xs text-white/50">
          <Switch checked={compact} onCheckedChange={setCompact} data-testid="compact-switch" />
          <span>Vue compacte</span>
        </div>
      </div>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <SectionCard title={`File POS (${orders.length})`}>
          {orders.length === 0 && (
            <div className="text-sm text-white/40 py-8 text-center">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              Aucune commande dans cet état.
            </div>
          )}
          <div className="space-y-2">
            {orders.map((o) => (
              <div key={o.id} data-testid={`pos-order-${o.id}`}
                className={`rounded-lg bg-white/[0.025] border border-white/[0.06] hover:border-white/[0.12] transition-all ${compact ? 'p-3' : 'p-4'}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-semibold">{o.order_number}</span>
                      <Badge color={statusColor(o.status)}>{o.status}</Badge>
                      <Badge color="#7c3aed">{o.fulfillment_type}</Badge>
                      {o.pay_with_uc && <Badge color="#D9B35A">PAYÉ UC</Badge>}
                    </div>
                    <div className="text-xs text-white/40 mt-1 flex items-center gap-3 flex-wrap">
                      <span><Calendar className="w-3 h-3 inline mr-1" />{new Date(o.created_at).toLocaleString('fr-FR')}</span>
                      <span><User className="w-3 h-3 inline mr-1" />{users[o.user_id]?.name || 'Client'}</span>
                      <span>{o.items?.length || 0} art. · <strong>{fmtEUR(o.total_cents)}</strong></span>
                      {o.pay_with_uc && <span className="text-[#D9B35A]">{o.total_uc} UC</span>}
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {o.status === 'PAID' && (
                      <Button size="sm" variant="outline" onClick={() => transitionTo(o.id, 'PREPARING')}
                        disabled={acting === o.id} data-testid={`btn-prepare-${o.id}`}>
                        <Package className="w-3 h-3 mr-1" /> Préparer
                      </Button>
                    )}
                    {o.status === 'PREPARING' && (
                      <Button size="sm" variant="outline" onClick={() => transitionTo(o.id, 'READY')}
                        disabled={acting === o.id} data-testid={`btn-ready-${o.id}`}>
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Marquer prête
                      </Button>
                    )}
                    {o.status === 'READY' && (
                      <Button size="sm"
                        onClick={() => lolodriveAPI.posScan(o.id).then(() => { toast.success('Retirée ✅'); load(); })}
                        disabled={acting === o.id} data-testid={`btn-scan-${o.id}`}
                        style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                        <ScanLine className="w-3 h-3 mr-1" /> Remettre client
                      </Button>
                    )}
                    {['PAID', 'PREPARING', 'READY', 'PENDING_PAYMENT', 'DRAFT'].includes(o.status) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
                        onClick={() => setCancelDialog({ open: true, order: o, reason: '', refundUc: !!o.pay_with_uc })}
                        disabled={acting === o.id}
                        data-testid={`btn-cancel-${o.id}`}
                      >
                        <XCircle className="w-3 h-3 mr-1" /> Annuler
                      </Button>
                    )}
                  </div>
                </div>
                {/* Items */}
                {!compact && o.items?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/5 grid sm:grid-cols-2 gap-2">
                    {o.items.map((it, idx) => (
                      <div key={idx} className="text-xs text-white/60 flex justify-between gap-2">
                        <span className="truncate">
                          <span className="text-white/80 font-medium">{it.qty}× </span>
                          {it.name}
                          {it.catalog_type === 'ESSENTIAL' && <Badge color="#D9B35A">E</Badge>}
                        </span>
                        <span className="text-white/40 shrink-0">
                          {fmtEUR((it.unit_cents || 0) * it.qty)}
                          {it.unit_uc && ` · ${it.unit_uc * it.qty} UC`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Footer help */}
      <div className="mt-6 text-xs text-white/40 text-center">
        {wsConnected ? '🟢 WebSocket temps réel actif' : autoRefresh ? '🟡 Polling fallback (30s)' : '⚪ Auto-refresh désactivé'} ·
        Son {soundOn ? 'on' : 'off'} ·
        Scannez un n° de commande pour retirer instantanément.
      </div>

      {/* Cancel dialog */}
      <Dialog open={cancelDialog.open} onOpenChange={(o) => setCancelDialog({ ...cancelDialog, open: o })}>
        <DialogContent className="bg-[#15151c] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>Annuler / signaler un problème</DialogTitle>
          </DialogHeader>
          {cancelDialog.order && (
            <div className="space-y-4">
              <div className="text-sm text-white/70">
                Commande <span className="font-mono font-semibold">{cancelDialog.order.order_number}</span> ·{' '}
                {fmtEUR(cancelDialog.order.total_cents)}
                {cancelDialog.order.pay_with_uc && <> · {cancelDialog.order.total_uc} UC</>}
              </div>
              <div>
                <Label className="text-xs text-white/60">Motif (visible client)</Label>
                <Textarea
                  value={cancelDialog.reason}
                  onChange={(e) => setCancelDialog({ ...cancelDialog, reason: e.target.value })}
                  placeholder="Produit indisponible, erreur de préparation, demande client…"
                  className="bg-white/[0.04] border-white/10 mt-1"
                  data-testid="cancel-reason"
                />
              </div>
              {cancelDialog.order.pay_with_uc && (
                <div className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <Switch
                    checked={cancelDialog.refundUc}
                    onCheckedChange={(v) => setCancelDialog({ ...cancelDialog, refundUc: v })}
                    data-testid="refund-uc-switch"
                  />
                  <div className="text-xs flex-1">
                    <div className="font-medium">Rembourser {cancelDialog.order.total_uc} UC au client</div>
                    <div className="text-white/50">Recommandé pour les commandes payées en UC</div>
                  </div>
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setCancelDialog({ ...cancelDialog, open: false })}>
                  Retour
                </Button>
                <Button onClick={confirmCancel} disabled={acting === cancelDialog.order.id}
                  data-testid="confirm-cancel-btn"
                  className="bg-red-500 hover:bg-red-600 text-white">
                  <XCircle className="w-3 h-3 mr-2" /> Confirmer l'annulation
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </LolodriveLayout>
  );
}

const statusColor = (s) => {
  if (s === 'FULFILLED') return '#10b981';
  if (s === 'READY') return '#D9B35A';
  if (s === 'PREPARING' || s === 'PAID') return '#3b82f6';
  return '#7c3aed';
};
