import React, { useEffect, useState } from 'react';
import { Store, Plus, MapPin, RefreshCw, Calculator, TrendingUp } from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

export default function LoloPointsAdminPage() {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openNew, setOpenNew] = useState(false);
  const [form, setForm] = useState({ name: '', code: '', city: '', address: '', zone_name: '' });
  const [payoutOpen, setPayoutOpen] = useState(false);
  const [payoutPoint, setPayoutPoint] = useState(null);
  const [payoutResult, setPayoutResult] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const r = await lolodriveAPI.listLoloPoints();
      setPoints(r.points || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const createPoint = async () => {
    try {
      await lolodriveAPI.createLoloPoint({
        ...form,
        payout_cap_cents_monthly: 120000,
        payout_cap_percent_bps: 600,
      });
      toast.success('Lolo Point créé');
      setOpenNew(false);
      setForm({ name: '', code: '', city: '', address: '', zone_name: '' });
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
      title="Gestion LOLO POINTS"
      subtitle="Réseau coopératif de relais. Commissions plafonnées par règles ESS."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Dialog open={openNew} onOpenChange={setOpenNew}>
            <DialogTrigger asChild>
              <Button size="sm" data-testid="new-point-btn"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                <Plus className="w-4 h-4 mr-2" /> Nouveau Lolo Point
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#15151c] border-white/10 text-white">
              <DialogHeader>
                <DialogTitle>Créer un Lolo Point</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard testId="kpi-total-points" label="Lolo Points actifs" value={points.length} icon={Store} accent="#7c3aed" />
        <KpiCard testId="kpi-cities" label="Villes couvertes" value={new Set(points.map(p => p.city)).size} icon={MapPin} accent="#10b981" />
        <KpiCard testId="kpi-cap-monthly" label="Plafond mensuel" value="1 200 €" sub="par point" icon={Calculator} accent="#D9B35A" />
        <KpiCard testId="kpi-cap-percent" label="Plafond %" value="6%" sub="du volume" icon={TrendingUp} accent="#ec4899" />
      </div>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <div className="grid md:grid-cols-2 gap-4">
          {points.map((p) => (
            <SectionCard key={p.id} className="hover:border-white/[0.15] transition-all">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="font-semibold">{p.name}</div>
                  <div className="text-xs text-white/40 font-mono">{p.code}</div>
                </div>
                <Badge color="#10b981">{p.status}</Badge>
              </div>
              <div className="text-xs text-white/60 space-y-1 mb-3">
                <div><MapPin className="w-3 h-3 inline mr-1" />{p.address}, {p.city}</div>
                {p.zone_name && <div>Zone : {p.zone_name}</div>}
              </div>
              <Button size="sm" variant="outline" className="w-full"
                onClick={() => previewPayout(p)} data-testid={`payout-${p.id}`}>
                <Calculator className="w-3 h-3 mr-2" /> Aperçu commissions (30j)
              </Button>
            </SectionCard>
          ))}
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
