import React, { useEffect, useState } from 'react';
import {
  Sparkles, Plus, Calendar, Zap, Users, RefreshCw, Building2, Eye,
  Package, AlertCircle, Clock, CheckCircle2, X, Ticket,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

const EVENT_TYPES = ['LOLO_HOUR', 'FLASH_PASS', 'FLASH_PUBLIC', 'LOLO_BIG_DEAL', 'PARTNER'];
const SCOPES = [
  { id: 'upcoming', label: 'Planifiés' },
  { id: 'live', label: 'En cours' },
  { id: 'ended', label: 'Terminés' },
  { id: 'all', label: 'Tous' },
];

const colorFor = (t) => ({
  LOLO_HOUR: '#D9B35A',
  FLASH_PASS: '#ec4899',
  FLASH_PUBLIC: '#3b82f6',
  LOLO_BIG_DEAL: '#7c3aed',
  PARTNER: '#10b981',
}[t] || '#888');

export default function LoloHourAdminPage() {
  const [scope, setScope] = useState('upcoming');
  const [events, setEvents] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openNew, setOpenNew] = useState(false);
  const [detailEvent, setDetailEvent] = useState(null);
  const [detailReservations, setDetailReservations] = useState([]);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkedItems, setLinkedItems] = useState([]); // [{sku, flash_price_cents, flash_price_uc}]

  const [form, setForm] = useState({
    type: 'LOLO_HOUR', title: '',
    starts_at: '', ends_at: '',
    is_pass_only: true, drive_only: true,
    per_user_limit: 1, stock_limit: 50,
    sponsor_pack: '',
  });

  const load = async () => {
    try {
      setLoading(true);
      const [evs, prods] = await Promise.all([
        lolodriveAPI.listEvents(scope),
        lolodriveAPI.catalogProducts(),
      ]);
      setEvents(evs.events || []);
      setProducts(prods.products || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [scope]);

  const createEv = async () => {
    try {
      const payload = {
        ...form,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
        per_user_limit: parseInt(form.per_user_limit) || 1,
        stock_limit: parseInt(form.stock_limit) || 0,
      };
      if (!payload.sponsor_pack) delete payload.sponsor_pack;
      await lolodriveAPI.createEvent(payload);
      toast.success('Événement créé');
      setOpenNew(false);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const openDetail = async (ev) => {
    setDetailEvent(ev);
    setDetailReservations([]);
    try {
      const [full, resv] = await Promise.all([
        lolodriveAPI.eventDetail(ev.id),
        lolodriveAPI.listEventReservations(ev.id),
      ]);
      setDetailEvent(full);
      setDetailReservations(resv.reservations || []);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const openLinkProducts = (ev) => {
    setDetailEvent(ev);
    setLinkedItems((ev.linked_products || []).map((lp) => ({
      sku: lp.sku, flash_price_cents: lp.flash_price_cents || lp.public_price_cents || 0, flash_price_uc: lp.flash_price_uc || 0,
    })));
    setLinkOpen(true);
  };

  const saveLinks = async () => {
    try {
      await lolodriveAPI.linkProductsToEvent(detailEvent.id, linkedItems);
      toast.success('Produits liés mis à jour');
      setLinkOpen(false);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const stats = {
    total: events.length,
    pass_only: events.filter((e) => e.is_pass_only).length,
    upcoming: events.filter((e) => new Date(e.starts_at) > new Date()).length,
    full: events.filter((e) => e.stock_limit && (e.reservations_count || 0) >= e.stock_limit).length,
  };

  return (
    <LolodriveLayout
      title="LOLO HOUR"
      subtitle="Événements horaires, flashs PASS et activations partenaires sponsors."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Dialog open={openNew} onOpenChange={setOpenNew}>
            <DialogTrigger asChild>
              <Button size="sm" data-testid="new-event-btn"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                <Plus className="w-4 h-4 mr-2" /> Nouvel événement
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-lg">
              <DialogHeader>
                <DialogTitle>Créer un événement LOLO</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-white/60">Type</Label>
                  <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10 mt-1" data-testid="ev-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {EVENT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Field label="Titre" v={form.title} onChange={(v) => setForm({ ...form, title: v })} testId="ev-title" />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Début" type="datetime-local" v={form.starts_at} onChange={(v) => setForm({ ...form, starts_at: v })} testId="ev-starts" />
                  <Field label="Fin" type="datetime-local" v={form.ends_at} onChange={(v) => setForm({ ...form, ends_at: v })} testId="ev-ends" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Limite / user" type="number" v={form.per_user_limit} onChange={(v) => setForm({ ...form, per_user_limit: v })} testId="ev-perlimit" />
                  <Field label="Stock total" type="number" v={form.stock_limit} onChange={(v) => setForm({ ...form, stock_limit: v })} testId="ev-stock" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2">
                    <Switch checked={form.is_pass_only} onCheckedChange={(v) => setForm({ ...form, is_pass_only: v })} data-testid="ev-pass-only" />
                    <Label className="text-xs text-white/70">PASS uniquement</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch checked={form.drive_only} onCheckedChange={(v) => setForm({ ...form, drive_only: v })} data-testid="ev-drive-only" />
                    <Label className="text-xs text-white/70">Drive uniquement</Label>
                  </div>
                </div>
                {form.type === 'PARTNER' && (
                  <Field label="Sponsor pack (GOLD/SILVER)" v={form.sponsor_pack} onChange={(v) => setForm({ ...form, sponsor_pack: v })} testId="ev-sponsor" />
                )}
                <Button onClick={createEv} className="w-full" data-testid="ev-create-confirm"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                  Créer l'événement
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </>
      }
    >
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard testId="kpi-total" label="Événements" value={stats.total} icon={Sparkles} accent="#D9B35A" />
        <KpiCard testId="kpi-pass-only" label="PASS uniquement" value={stats.pass_only} icon={Ticket} accent="#ec4899" />
        <KpiCard testId="kpi-upcoming" label="À venir" value={stats.upcoming} icon={Calendar} accent="#3b82f6" />
        <KpiCard testId="kpi-full" label="Complets" value={stats.full} icon={AlertCircle} accent="#ef4444" />
      </div>

      <Tabs value={scope} onValueChange={setScope} className="mb-4">
        <TabsList className="bg-white/[0.04] border border-white/10">
          {SCOPES.map((s) => (
            <TabsTrigger key={s.id} value={s.id} data-testid={`scope-${s.id}`}>{s.label}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <SectionCard title={`${events.length} événement(s)`}>
          {events.length === 0 && (
            <div className="text-sm text-white/40 py-8 text-center">Aucun événement.</div>
          )}
          <div className="grid md:grid-cols-2 gap-3">
            {events.map((ev) => {
              const fillRatio = ev.stock_limit ? (ev.reservations_count || 0) / ev.stock_limit : 0;
              const isPast = new Date(ev.ends_at) < new Date();
              const isLive = !isPast && new Date(ev.starts_at) <= new Date();
              return (
                <div key={ev.id} data-testid={`event-${ev.id}`}
                  className="rounded-lg bg-white/[0.025] border border-white/[0.06] p-4 hover:border-white/[0.15] transition-all">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="font-semibold leading-tight flex-1">{ev.title}</div>
                    <Badge color={colorFor(ev.type)}>{ev.type}</Badge>
                  </div>
                  <div className="text-xs text-white/50 mb-3">
                    <Calendar className="w-3 h-3 inline mr-1" />
                    {new Date(ev.starts_at).toLocaleString('fr-FR')} → {new Date(ev.ends_at).toLocaleString('fr-FR')}
                    {isLive && <Badge color="#10b981" className="ml-2">EN COURS</Badge>}
                    {isPast && <Badge color="#888" className="ml-2">TERMINÉ</Badge>}
                  </div>
                  <div className="flex gap-2 flex-wrap mb-3">
                    {ev.is_pass_only && <Badge color="#D9B35A">PASS</Badge>}
                    {ev.drive_only && <Badge color="#7c3aed">DRIVE</Badge>}
                    {ev.sponsor_pack && <Badge color="#10b981">{ev.sponsor_pack}</Badge>}
                  </div>
                  {ev.stock_limit && (
                    <div className="mb-3">
                      <div className="flex justify-between text-[11px] text-white/50 mb-1">
                        <span><Users className="w-3 h-3 inline mr-1" />Réservations</span>
                        <span>{ev.reservations_count || 0} / {ev.stock_limit}</span>
                      </div>
                      <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(100, fillRatio * 100)}%`,
                            background: fillRatio >= 1 ? '#ef4444' : fillRatio >= 0.8 ? '#f59e0b' : '#10b981',
                          }}
                        />
                      </div>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => openDetail(ev)}
                      data-testid={`detail-${ev.id}`}>
                      <Eye className="w-3 h-3 mr-1" /> Détail
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => openLinkProducts(ev)}
                      data-testid={`link-${ev.id}`}>
                      <Package className="w-3 h-3 mr-1" />
                      {(ev.linked_products || []).length > 0 ? `${ev.linked_products.length} produit(s)` : 'Lier produits'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* Event detail dialog */}
      <Dialog open={!!detailEvent && !linkOpen} onOpenChange={(o) => !o && setDetailEvent(null)}>
        <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{detailEvent?.title}</DialogTitle>
          </DialogHeader>
          {detailEvent && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <StatRow label="Réservations" value={detailEvent.reservations_count || 0} />
                <StatRow label="Stock total" value={detailEvent.stock_limit || '∞'} />
                <StatRow label="Restant" value={detailEvent.remaining_stock ?? '∞'} />
              </div>
              {detailEvent.linked_products?.length > 0 && (
                <div>
                  <div className="text-xs text-white/60 mb-2 font-semibold uppercase tracking-wider">Produits flash</div>
                  <div className="space-y-1">
                    {detailEvent.linked_products.map((lp) => (
                      <div key={lp.sku} className="flex justify-between p-2 rounded bg-white/[0.03] text-sm">
                        <span>{lp.name || lp.sku}</span>
                        <span className="text-[#D9B35A]">
                          {((lp.flash_price_cents || 0) / 100).toFixed(2)} €
                          {lp.flash_price_uc && ` · ${lp.flash_price_uc} UC`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="text-xs text-white/60 mb-2 font-semibold uppercase tracking-wider">
                  Réservations ({detailReservations.length})
                </div>
                {detailReservations.length === 0 && (
                  <div className="text-sm text-white/40 py-2">Aucune réservation.</div>
                )}
                <div className="space-y-1 max-h-[200px] overflow-y-auto">
                  {detailReservations.map((r) => (
                    <div key={r.id} className="flex items-center justify-between p-2 rounded bg-white/[0.02] text-xs">
                      <div>
                        <div className="font-medium">{r.user_name || r.user_id.slice(0, 12)}</div>
                        <div className="text-white/40">{r.user_email}</div>
                      </div>
                      <Badge color={r.status === 'CONFIRMED' ? '#10b981' : '#888'}>{r.status}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Link products dialog */}
      <Dialog open={linkOpen} onOpenChange={setLinkOpen}>
        <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Produits flash — {detailEvent?.title}</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-white/50 mb-3">
            Choisissez les produits inclus dans l'événement avec leur prix flash (en cents) et en UC.
          </p>
          <div className="space-y-2 max-h-[50vh] overflow-y-auto">
            {products.map((p) => {
              const linked = linkedItems.find((li) => li.sku === p.sku);
              return (
                <div key={p.sku} className="flex items-center gap-3 p-2 rounded bg-white/[0.02] border border-white/[0.05]">
                  <Switch
                    checked={!!linked}
                    onCheckedChange={(on) => {
                      if (on) setLinkedItems([...linkedItems, { sku: p.sku, flash_price_cents: p.price_pass_cents || p.price_public_cents, flash_price_uc: Math.round((p.price_pass_cents || p.price_public_cents) / 10) }]);
                      else setLinkedItems(linkedItems.filter((li) => li.sku !== p.sku));
                    }}
                    data-testid={`link-toggle-${p.sku}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{p.name}</div>
                    <div className="text-[10px] text-white/40">{p.sku} · {p.catalog_type} · public {((p.price_public_cents || 0) / 100).toFixed(2)}€</div>
                  </div>
                  {linked && (
                    <div className="flex gap-2 shrink-0">
                      <input
                        type="number"
                        value={linked.flash_price_cents}
                        onChange={(e) => setLinkedItems(linkedItems.map((li) => li.sku === p.sku ? { ...li, flash_price_cents: parseInt(e.target.value) || 0 } : li))}
                        className="w-20 bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs"
                        placeholder="cents"
                      />
                      <input
                        type="number"
                        value={linked.flash_price_uc}
                        onChange={(e) => setLinkedItems(linkedItems.map((li) => li.sku === p.sku ? { ...li, flash_price_uc: parseInt(e.target.value) || 0 } : li))}
                        className="w-16 bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs"
                        placeholder="UC"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <Button onClick={saveLinks} className="w-full mt-3" data-testid="save-links-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            Enregistrer ({linkedItems.length} produit(s))
          </Button>
        </DialogContent>
      </Dialog>
    </LolodriveLayout>
  );
}

const Field = ({ label, v, onChange, type = 'text', testId }) => (
  <div>
    <Label className="text-xs text-white/60">{label}</Label>
    <Input type={type} value={v} onChange={(e) => onChange(e.target.value)} data-testid={testId}
      className="bg-white/[0.04] border-white/10 mt-1" />
  </div>
);

const StatRow = ({ label, value }) => (
  <div className="p-3 rounded bg-white/[0.03] border border-white/[0.06]">
    <div className="text-lg font-bold">{value}</div>
    <div className="text-[10px] text-white/40 mt-0.5">{label}</div>
  </div>
);
