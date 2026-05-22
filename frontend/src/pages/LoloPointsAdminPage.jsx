import React, { useEffect, useMemo, useState } from 'react';
import { Store, Plus, MapPin, RefreshCw, Calculator, TrendingUp, Map as MapIcon, List } from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import Phase2Banner from '../components/Phase2Banner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { lolodriveAPI } from '../services/api';
import { toast } from 'sonner';
import TerritorySelector, { getInitialTerritory } from '../components/TerritorySelector';
import LoloPointsMap from '../components/LoloPointsMap';

export default function LoloPointsAdminPage() {
  const [points, setPoints] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [territory, setTerritory] = useState(getInitialTerritory());
  const [view, setView] = useState('map'); // 'map' | 'list'
  const [loading, setLoading] = useState(true);
  const [openNew, setOpenNew] = useState(false);
  const [form, setForm] = useState({ name: '', code: '', city: '', address: '', zone_name: '', territory: 'GP', lat: '', lng: '' });
  const [payoutOpen, setPayoutOpen] = useState(false);
  const [payoutPoint, setPayoutPoint] = useState(null);
  const [payoutResult, setPayoutResult] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const [pts, terr] = await Promise.all([
        lolodriveAPI.listLoloPoints({ territory }),
        territories.length === 0 ? lolodriveAPI.listTerritories() : Promise.resolve({ territories }),
      ]);
      setPoints(pts.points || []);
      if (terr.territories) setTerritories(terr.territories);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [territory]);

  const filteredPoints = useMemo(() => points, [points]);
  const citiesCovered = useMemo(() => new Set(filteredPoints.map((p) => p.city).filter(Boolean)).size, [filteredPoints]);
  const territoriesCovered = useMemo(() => new Set(filteredPoints.map((p) => p.territory).filter(Boolean)).size, [filteredPoints]);

  const createPoint = async () => {
    try {
      const payload = {
        ...form,
        lat: form.lat ? parseFloat(form.lat) : undefined,
        lng: form.lng ? parseFloat(form.lng) : undefined,
        payout_cap_cents_monthly: 120000,
        payout_cap_percent_bps: 600,
      };
      await lolodriveAPI.createLoloPoint(payload);
      toast.success('Relais LOLODRIVE créé');
      setOpenNew(false);
      setForm({ name: '', code: '', city: '', address: '', zone_name: '', territory: 'GP', lat: '', lng: '' });
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const previewPayout = async (point) => {
    setPayoutPoint(point);
    setPayoutResult(null);
    setPayoutOpen(true);
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - 30);
    try {
      const r = await lolodriveAPI.payoutPreview(point.id, from.toISOString(), to.toISOString());
      setPayoutResult(r);
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <LolodriveLayout
      title="Réseau LOLODRIVE"
      subtitle="Relais coopératifs multi-territoires (Antilles · Guyane · Réunion)"
      actions={
        <>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Dialog open={openNew} onOpenChange={setOpenNew}>
            <DialogTrigger asChild>
              <Button size="sm" data-testid="new-point-btn"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                <Plus className="w-4 h-4 mr-2" /> Nouveau relais
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#15151c] border-white/10 text-white">
              <DialogHeader>
                <DialogTitle>Créer un Relais LOLODRIVE</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-white/60">Territoire</Label>
                  <select
                    value={form.territory}
                    onChange={(e) => setForm({ ...form, territory: e.target.value })}
                    className="w-full mt-1 bg-white/[0.04] border border-white/10 rounded-md px-3 py-2 text-sm"
                    data-testid="new-point-territory"
                  >
                    {territories.map((t) => (
                      <option key={t.code} value={t.code} className="bg-[#15151c]">{t.name} ({t.code})</option>
                    ))}
                  </select>
                </div>
                {[
                  { k: 'name', l: 'Nom' },
                  { k: 'code', l: 'Code (ex: LP-PAP)' },
                  { k: 'city', l: 'Ville' },
                  { k: 'address', l: 'Adresse' },
                  { k: 'zone_name', l: 'Zone' },
                ].map((f) => (
                  <div key={f.k}>
                    <Label className="text-xs text-white/60">{f.l}</Label>
                    <Input value={form[f.k]} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })}
                      className="bg-white/[0.04] border-white/10 mt-1" data-testid={`new-point-${f.k}`} />
                  </div>
                ))}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs text-white/60">Latitude</Label>
                    <Input value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })}
                      placeholder="16.2418" className="bg-white/[0.04] border-white/10 mt-1" data-testid="new-point-lat" />
                  </div>
                  <div>
                    <Label className="text-xs text-white/60">Longitude</Label>
                    <Input value={form.lng} onChange={(e) => setForm({ ...form, lng: e.target.value })}
                      placeholder="-61.5331" className="bg-white/[0.04] border-white/10 mt-1" data-testid="new-point-lng" />
                  </div>
                </div>
                <Button onClick={createPoint} className="w-full" data-testid="create-point-confirm-btn"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                  Créer
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </>
      }
    >
      <Phase2Banner module="Réseau LOLODRIVE" />

      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <TerritorySelector
          territories={territories}
          value={territory}
          onChange={setTerritory}
          testId="lolo-territory-selector"
        />
        <div className="inline-flex rounded-full border border-white/10 bg-white/[0.04] p-1">
          <button
            onClick={() => setView('map')}
            data-testid="view-map-btn"
            className={`px-3 py-1.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5 ${
              view === 'map' ? 'bg-[#D9B35A] text-black' : 'text-white/70 hover:bg-white/[0.06]'
            }`}
          >
            <MapIcon className="w-3.5 h-3.5" /> Carte
          </button>
          <button
            onClick={() => setView('list')}
            data-testid="view-list-btn"
            className={`px-3 py-1.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5 ${
              view === 'list' ? 'bg-[#D9B35A] text-black' : 'text-white/70 hover:bg-white/[0.06]'
            }`}
          >
            <List className="w-3.5 h-3.5" /> Liste
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard testId="kpi-total-points" label="Relais actifs" value={filteredPoints.length} icon={Store} accent="#7c3aed" />
        <KpiCard testId="kpi-territories" label="Territoires" value={territoriesCovered} icon={MapPin} accent="#10b981" />
        <KpiCard testId="kpi-cities" label="Villes couvertes" value={citiesCovered} icon={MapPin} accent="#06b6d4" />
        <KpiCard testId="kpi-cap-monthly" label="Plafond mensuel" value="1 200 €" sub="par point" icon={Calculator} accent="#D9B35A" />
      </div>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && view === 'map' && (
        <div className="mb-6">
          <LoloPointsMap points={filteredPoints} territory={territory} onSelect={(p) => previewPayout(p)} height="520px" />
          <p className="text-[11px] text-white/40 mt-2">Cliquez sur un marqueur pour ouvrir l'aperçu commissions sur 30 jours.</p>
        </div>
      )}

      {!loading && view === 'list' && (
        <div className="grid md:grid-cols-2 gap-4">
          {filteredPoints.map((p) => (
            <SectionCard key={p.id} className="hover:border-white/[0.15] transition-all" data-testid={`lolo-point-card-${p.code}`}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="font-semibold">{p.name}</div>
                  <div className="text-xs text-white/40 font-mono">{p.code} · {p.territory || '—'}</div>
                </div>
                <Badge color="#10b981">{p.status}</Badge>
              </div>
              <div className="text-xs text-white/60 space-y-1 mb-3">
                <div><MapPin className="w-3 h-3 inline mr-1" />{p.address || '—'}, {p.city || '—'}</div>
                {p.zone_name && <div>Zone : {p.zone_name}</div>}
              </div>
              <Button size="sm" variant="outline" className="w-full"
                onClick={() => previewPayout(p)} data-testid={`payout-${p.id}`}>
                <Calculator className="w-3 h-3 mr-2" /> Aperçu commissions (30j)
              </Button>
            </SectionCard>
          ))}
          {filteredPoints.length === 0 && (
            <div className="md:col-span-2 text-center text-white/50 py-12 text-sm" data-testid="empty-points">
              Aucun relais LOLODRIVE pour ce territoire.
            </div>
          )}
        </div>
      )}

      <Dialog open={payoutOpen} onOpenChange={setPayoutOpen}>
        <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-2xl">
          <DialogHeader>
            <DialogTitle>Aperçu commissions — {payoutPoint?.name}</DialogTitle>
          </DialogHeader>
          {!payoutResult && <div className="text-sm text-white/50 py-4">Calcul en cours…</div>}
          {payoutResult && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Volume conso" value={fmtEUR(payoutResult.consumption_volume_cents)} />
                <Stat label="Retraits" value={payoutResult.withdrawals} />
                <Stat label="Activations PASS" value={payoutResult.pass_activations} />
              </div>
              <div className="rounded-lg p-3 bg-white/[0.03] border border-white/[0.06]">
                <div className="text-xs text-white/40 mb-2">Composants commission</div>
                <div className="space-y-1 text-xs">
                  <Row label="Commission retraits" value={fmtEUR(payoutResult.components.withdrawal_commission_cents)} />
                  <Row label="Commission activations PASS" value={fmtEUR(payoutResult.components.pass_commission_cents)} />
                  <Row label="Commission volume essentiels" value={fmtEUR(payoutResult.components.volume_commission_cents)} />
                </div>
              </div>
              <div className="rounded-lg p-3 bg-[#D9B35A]/[0.05] border border-[#D9B35A]/30">
                <div className="text-xs text-white/40 mb-2">Plafonds ESS</div>
                <div className="space-y-1 text-xs">
                  <Row label="Calculé" value={fmtEUR(payoutResult.calculated_cents)} />
                  <Row label="Plafond %" value={fmtEUR(payoutResult.caps.percent_cap_cents)} />
                  <Row label="Plafond mensuel" value={fmtEUR(payoutResult.caps.monthly_cap_cents)} />
                  <div className="border-t border-white/10 pt-1 mt-1 flex justify-between font-bold text-[#D9B35A]">
                    <span>À verser (plafonné)</span>
                    <span>{fmtEUR(payoutResult.capped_cents)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </LolodriveLayout>
  );
}

const Stat = ({ label, value }) => (
  <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3">
    <div className="text-base font-bold">{value}</div>
    <div className="text-[10px] text-white/40 mt-0.5">{label}</div>
  </div>
);
const Row = ({ label, value }) => (
  <div className="flex justify-between">
    <span className="text-white/60">{label}</span>
    <span className="font-medium">{value}</span>
  </div>
);
