import { RoleSpaceLayout, KpiCard, QuickLink } from '../components/RoleSpaceLayout';

export default function ExpertSpacePage() {
  return (
    <RoleSpaceLayout
      title="Espace Expert"
      subtitle="Consultation & conseil : vue d'ensemble de l'activité de la coopérative (lecture seule)."
      badgeColor="#5B2E8C"
      roleName="EXPERT"
      testId="expert-space-page"
    >
      {(overview) => (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="Membres inscrits" value={overview.kpis.users_total} color="#5B2E8C" testId="expert-kpi-users" />
            <KpiCard label="Produits référencés" value={overview.kpis.products_total} testId="expert-kpi-products" />
            <KpiCard label="Commandes cumulées" value={overview.kpis.orders_total} color="#6FA82E" testId="expert-kpi-orders" />
            <KpiCard label="Produits en validation" value={overview.kpis.vendor_products_pending} color="#E67E22" testId="expert-kpi-pending" />
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5" data-testid="expert-note">
            <h3 className="font-display text-lg mb-2 text-[#1F2A3A]">Mission conseil</h3>
            <p className="text-sm opacity-70">
              En tant qu&apos;Expert, vous disposez d&apos;un accès en consultation sur les indicateurs de la coopérative
              pour accompagner la gouvernance ESS : analyse des volumes mutualisés, structure du catalogue
              et dynamique des commandes. Pour toute recommandation, contactez le conseil coopératif.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <QuickLink to="/catalogue" label="Consulter le catalogue" />
            <QuickLink to="/reporting-impact" label="Reporting d'impact" />
            <QuickLink to="/statistiques" label="Statistiques" />
          </div>
        </div>
      )}
    </RoleSpaceLayout>
  );
}
