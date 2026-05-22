import React, { useEffect, useState } from 'react';
import { Sparkles, Plus, Calendar, Zap, Users, RefreshCw, Building2 } from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge } from '../components/LolodriveLayout';
import Phase2Banner from '../components/Phase2Banner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

const EVENT_TYPES = ['LOLO_HOUR', 'FLASH_PASS', 'FLASH_PUBLIC', 'LOLO_BIG_DEAL', 'PARTNER'];

const colorFor = (t) => ({
  LOLO_HOUR: '#D9B35A',
  FLASH_PASS: '#ec4899',
  FLASH_PUBLIC: '#3b82f6',
  LOLO_BIG_DEAL: '#7c3aed',
  PARTNER: '#10b981',
}[t] || '#888');

export default function LoloHourAdminPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openNew, setOpenNew] = useState(false);
  const [form, setForm] = useState({
    type: 'LOLO_HOUR',
    title: '',
    starts_at: '',
    ends_at: '',
    is_pass_only: true,
    drive_only: true,
    per_user_limit: 1,
    stock_limit: 100,
    sponsor_pack: '',
    partner_id: '',
  });

  const load = async () => {
    try {
      setLoading(true);
      const r = await lolodriveAPI.activeEvents();
      setEvents(r.events || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const createEv = async () => {
    try {
      const payload = {
        ...form,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
        per_user_limit: parseInt(form.per_user_limit) || 1,
        stock_limit: parseInt(form.stock_limit) || 0,
      };
      if (!payload.partner_id) delete payload.partner_id;
      if (!payload.sponsor_pack) delete payload.sponsor_pack;
      await lolodriveAPI.createEvent(payload);
      toast.success('Événement créé');
      setOpenNew(false);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const byType = EVENT_TYPES.reduce((acc, t) => { acc[t] = events.filter(e => e.type === t).length; return acc; }, {});

  return (
    <LolodriveLayout
      title="Gestion LOLO HOUR"
      subtitle="Événements horaires, flash PASS et activations partenaires sponsors."
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
                  <Field label="Limite par user" type="number" v={form.per_user_limit} onChange={(v) => setForm({ ...form, per_user_limit: v })} testId="ev-perlimit" />
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
                  <Field label="Sponsor pack (GOLD/SILVER/...)" v={form.sponsor_pack} onChange={(v) => setForm({ ...form, sponsor_pack: v })} testId="ev-sponsor" />
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
      <Phase2Banner module="LOLO HOUR" />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {EVENT_TYPES.map((t) => (
          <KpiCard key={t} testId={`kpi-${t}`} label={t.replace('_', ' ')} value={byType[t] || 0}
            icon={t === 'PARTNER' ? Building2 : t === 'FLASH_PASS' || t === 'FLASH_PUBLIC' ? Zap : Sparkles}
            accent={colorFor(t)} />
        ))}
      </div>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <SectionCard title={`Événements actifs (${events.length})`}>
          {events.length === 0 && (
            <div className="text-sm text-white/40 py-8 text-center">Aucun événement actif.</div>
          )}
          <div className="grid md:grid-cols-2 gap-3">
            {events.map((ev) => (
              <div key={ev.id} data-testid={`event-${ev.id}`}
                className="rounded-lg bg-white/[0.025] border border-white/[0.06] p-4 hover:border-white/[0.15] transition-all">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="font-semibold leading-tight">{ev.title}</div>
                  <Badge color={colorFor(ev.type)}>{ev.type}</Badge>
                </div>
                <div className="text-xs text-white/50 space-y-1">
                  <div><Calendar className="w-3 h-3 inline mr-1" />
                    {new Date(ev.starts_at).toLocaleString('fr-FR')} → {new Date(ev.ends_at).toLocaleString('fr-FR')}
                  </div>
                  <div className="flex gap-2 flex-wrap mt-2">
                    {ev.is_pass_only && <Badge color="#D9B35A">PASS</Badge>}
                    {ev.drive_only && <Badge color="#7c3aed">DRIVE</Badge>}
                    {ev.stock_limit && <Badge color="#3b82f6"><Users className="w-3 h-3 mr-1 inline" />{ev.stock_limit} places</Badge>}
                    {ev.sponsor_pack && <Badge color="#10b981">{ev.sponsor_pack}</Badge>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
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
