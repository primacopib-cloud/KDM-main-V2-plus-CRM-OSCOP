import { RoleSpaceLayout, KpiCard, QuickLink } from '../components/RoleSpaceLayout';

const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString('fr-FR'); } catch (_e) { return '—'; } };

export default function CooperSpacePage() {
  return (
    <RoleSpaceLayout
      title="Espace COOPER"
      subtitle="Suivi opérationnel de la coopérative : commandes, produits et stocks."
      badgeColor="#6FA82E"
      roleName="COOPER"
      testId="cooper-space-page"
    >
      {(overview) => (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="Commandes" value={overview.kpis.orders_total} color="#6FA82E" testId="cooper-kpi-orders" />
            <KpiCard label="Produits catalogue" value={overview.kpis.products_total} testId="cooper-kpi-products" />
            <KpiCard label="Produits à valider" value={overview.kpis.vendor_products_pending} color="#E64432" testId="cooper-kpi-pending" />
            <KpiCard label="Stocks faibles" value={overview.kpis.low_stock} color="#E67E22" testId="cooper-kpi-lowstock" />
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5" data-testid="cooper-recent-orders">
            <h3 className="font-display text-lg mb-3 text-[#1F2A3A]">Dernières commandes</h3>
            {(overview.recent_orders || []).length === 0 ? (
              <p className="text-sm opacity-50 py-3">Aucune commande récente.</p>
            ) : (
              <div className="divide-y divide-black/5">
                {overview.recent_orders.map((o) => (
                  <div key={o.id} className="flex items-center justify-between py-2 text-sm">
                    <span className="font-mono text-xs opacity-60">{o.id}</span>
                    <span className="opacity-60">{fmtDate(o.created_at)}</span>
                    <span className="font-medium">{(o.total_ttc || 0).toFixed(2)} €</span>
                    <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-black/5">{o.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <QuickLink to="/catalogue" label="Catalogue B2B" />
            <QuickLink to="/commandes" label="Commandes" />
            <QuickLink to="/lolodrive" label="LOLODRIVE" />
          </div>
        </div>
      )}
    </RoleSpaceLayout>
  );
}
