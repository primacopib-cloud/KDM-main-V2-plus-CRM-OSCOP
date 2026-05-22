import React, { useEffect, useState } from 'react';
import { Leaf, Ticket, Store, Building2, ShoppingBag, Wallet, RefreshCw, Download, HeartHandshake, Briefcase } from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import Phase2Banner from '../components/Phase2Banner';
import { Button } from '../components/ui/button';
import { crmAPI, lolodriveAPI } from '../services/api';
import { toast } from 'sonner';

export default function EssReportingPage() {
  const [impact, setImpact] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const [i, k] = await Promise.all([
        crmAPI.impactSummary(),
        lolodriveAPI.kpiOverview(),
      ]);
      setImpact(i);
      setKpi(k);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ impact, kpi }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporting-impact-ess-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Rapport téléchargé');
  };

  return (
    <LolodriveLayout
      title="Reporting impact ESS"
      subtitle="Tableau de bord coopératif et indicateurs d'impact social, économique et territorial."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Button size="sm" onClick={downloadJSON} data-testid="download-btn"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
            <Download className="w-4 h-4 mr-2" /> Export JSON
          </Button>
        </>
      }
    >
      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && impact && kpi && (
        <>
          <Phase2Banner module="Reporting impact ESS" />
          {/* Hero */}
          <SectionCard className="mb-6 relative overflow-hidden">
            <div className="absolute -right-12 -top-12 w-48 h-48 rounded-full blur-3xl opacity-30 bg-emerald-400" />
            <div className="relative">
              <Badge color="#10b981">Impact ESS — temps réel</Badge>
              <h2 className="text-2xl font-bold mt-3">
                {impact.pass_active} foyers bénéficient du PASS Vie Chère
              </h2>
              <p className="text-sm text-white/60 mt-2 max-w-2xl">
                Un réseau coopératif de <strong>{impact.lolo_points_active} relais</strong> dans les territoires,
                soutenu par <strong>{impact.partners} partenaires</strong> de l'écosystème ESS local.
              </p>
              <p className="mt-4 text-xs text-white/40 italic border-l-2 border-emerald-400/60 pl-3">
                {impact.impact_positioning}
              </p>
            </div>
          </SectionCard>

          {/* Indicateurs sociaux */}
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Indicateurs sociaux</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-pass" label="Foyers protégés (PASS)" value={impact.pass_active} icon={Ticket} accent="#D9B35A" />
            <KpiCard testId="kpi-contacts" label="Contacts CRM" value={impact.crm_contacts} icon={HeartHandshake} accent="#ec4899" />
            <KpiCard testId="kpi-dossiers" label="Dossiers actifs" value={impact.crm_dossiers} icon={Briefcase} accent="#7c3aed" />
            <KpiCard testId="kpi-opps" label="Opportunités ESS" value={impact.crm_opportunities} icon={Leaf} accent="#10b981" />
          </div>

          {/* Indicateurs économiques */}
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Indicateurs économiques</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard testId="kpi-revenue" label="Chiffre d'affaires (30j)" value={fmtEUR(impact.revenue_cents)} icon={ShoppingBag} accent="#10b981" />
            <KpiCard testId="kpi-orders" label="Commandes honorées" value={impact.orders_paid} icon={ShoppingBag} accent="#3b82f6" />
            <KpiCard testId="kpi-uc-orders" label="Commandes payées en UC" value={impact.orders_paid_uc} sub={`${kpi.wallet?.debited_uc || 0} UC débités`} icon={Wallet} accent="#D9B35A" />
            <KpiCard testId="kpi-points" label="Lolo Points actifs" value={impact.lolo_points_active} icon={Store} accent="#7c3aed" />
          </div>

          {/* Pourcentage d'utilisation UC */}
          <SectionCard title="Utilisation du wallet UC" className="mb-6">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs text-white/60 mb-1">
                  <span>Commandes payées en UC</span>
                  <span>
                    {impact.orders_paid > 0
                      ? `${Math.round((impact.orders_paid_uc / impact.orders_paid) * 100)}%`
                      : '0%'}
                  </span>
                </div>
                <div className="h-2 bg-white/[0.05] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: impact.orders_paid > 0
                        ? `${Math.round((impact.orders_paid_uc / impact.orders_paid) * 100)}%`
                        : '0%',
                      background: 'linear-gradient(90deg, #D9B35A, #7c3aed)',
                    }}
                  />
                </div>
              </div>
              <p className="text-xs text-white/40">
                Mesure l'adoption du paiement en UC par les titulaires du PASS Vie Chère. Plus le ratio est élevé,
                plus l'écosystème coopératif circule en interne.
              </p>
            </div>
          </SectionCard>

          {/* Indicateurs réseau */}
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">Réseau territorial</h3>
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <SectionCard title="Drive">
              <div className="text-3xl font-bold">{kpi.orders?.drive || 0}</div>
              <div className="text-xs text-white/50 mt-1">commandes en retrait drive (30j)</div>
            </SectionCard>
            <SectionCard title="Livraison">
              <div className="text-3xl font-bold">{kpi.orders?.delivery || 0}</div>
              <div className="text-xs text-white/50 mt-1">livraisons à domicile (30j)</div>
            </SectionCard>
            <SectionCard title="Lolo Points">
              <div className="text-3xl font-bold">{kpi.orders?.lolo_point || 0}</div>
              <div className="text-xs text-white/50 mt-1">retraits en relais coopératif (30j)</div>
            </SectionCard>
          </div>

          {/* Note conformité */}
          <div className="rounded-2xl p-5 border border-emerald-500/30 bg-emerald-500/[0.04]">
            <div className="flex items-start gap-3">
              <Leaf className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold text-sm mb-2 text-emerald-400">Conformité ESS</div>
                <ul className="text-xs text-white/70 space-y-1 list-disc list-inside">
                  <li>Non-spéculation : les UC sont une unité d'usage interne, jamais convertibles en sortie.</li>
                  <li>Gouvernance coopérative : commissions LOLO POINTS plafonnées (1 200 €/mois et 6% du volume).</li>
                  <li>Mutualisation : tournées ESS regroupées entre territoires DOM.</li>
                  <li>Référence légale : prix en euros sur factures et reporting fiscal.</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </LolodriveLayout>
  );
}
