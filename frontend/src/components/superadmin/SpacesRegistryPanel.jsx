import { useCallback, useEffect, useState } from 'react';
import { Store, TrendingUp, MapPin, IdCard, ExternalLink, Ban, CheckCircle2, Loader2, Link2, Download, UserCog, Search } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { TerritoryFlag } from '../Flag';
import { SpaceDetailDialog, RelayManagerDialog } from './SpaceDetailDialog';

const SPACES = [
  { key: 'vendors', label: 'Vendeurs', icon: Store, route: '/vendor', active: 'APPROVED', suspend: 'SUSPENDED' },
  { key: 'investors', label: 'Investisseurs', icon: TrendingUp, route: '/espace-investisseur', active: 'ACTIVE', suspend: 'SUSPENDED' },
  { key: 'relays', label: 'Relais LOLODRIVE', icon: MapPin, route: '/lolo-point/dashboard', active: 'ACTIVE', suspend: 'SUSPENDED' },
  { key: 'pass_members', label: 'Membres PASS', icon: IdCard, route: '/pass', active: 'ACTIVE', suspend: 'SUSPENDED', patchKind: 'pass-members' },
];

const statusColor = (s) => {
  if (['ACTIVE', 'APPROVED'].includes(s)) return 'text-emerald-300 bg-emerald-500/15 border-emerald-400/30';
  if (['SUSPENDED', 'REJECTED', 'CANCELLED'].includes(s)) return 'text-red-300 bg-red-500/15 border-red-400/30';
  return 'text-amber-300 bg-amber-500/15 border-amber-400/30';
};

export const SpacesRegistryPanel = () => {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('vendors');
  const [busy, setBusy] = useState(null);
  const [detailRow, setDetailRow] = useState(null);
  const [managerRow, setManagerRow] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const load = useCallback(() => {
    fetch(`${API}/admin/spaces/registries`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setData(d))
      .catch(() => toast.error('Erreur de chargement des registres'));
  }, []);

  useEffect(() => { load(); }, [load]);

  const space = SPACES.find((s) => s.key === tab);
  const allRows = data?.[tab] || [];
  const statuses = [...new Set(allRows.map((r) => r.status).filter(Boolean))];
  const q = search.trim().toLowerCase();
  const rows = allRows.filter((r) =>
    (statusFilter === 'ALL' || r.status === statusFilter) &&
    (!q || (r.name || '').toLowerCase().includes(q) || (r.email || '').toLowerCase().includes(q)));

  const setStatus = async (row, status) => {
    setBusy(row.id);
    try {
      const r = await fetch(`${API}/admin/spaces/${space.patchKind || space.key}/${row.id}/status`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ status }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(status === space.suspend ? 'Espace suspendu' : 'Espace réactivé');
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  const exportCsv = () => {
    const header = ['Nom', 'Email', 'Téléphone', 'Pays', 'Détail', 'Compte lié', 'Statut', 'Inscrit le'];
    const lines = rows.map((r) => [r.name, r.email, r.phone, r.country, r.detail,
      r.account_connected ? 'Oui' : 'Non', r.status, String(r.created_at || '').slice(0, 10)]);
    const csv = [header, ...lines]
      .map((l) => l.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(';')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `registre-${space.key}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="rounded-[18px] p-5 bg-white/[0.04] border border-white/10" data-testid="spaces-registry-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-base font-semibold text-white">Registres des espaces</h2>
          <p className="text-xs text-white/50">Comptes enregistrés automatiquement et connectés à leur espace</p>
        </div>
        <button type="button" onClick={exportCsv} data-testid="spaces-export-csv"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] border border-white/15 text-white/75 hover:text-white">
          <Download className="w-3.5 h-3.5" /> Exporter CSV ({rows.length})
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {SPACES.map((s) => (
          <button key={s.key} type="button" onClick={() => { setTab(s.key); setSearch(''); setStatusFilter('ALL'); }} data-testid={`spaces-tab-${s.key}`}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              tab === s.key ? 'bg-[#D9B35A]/20 border-[#D9B35A]/50 text-[#E9CF8E]' : 'bg-white/[0.04] border-white/10 text-white/60 hover:text-white'}`}>
            <s.icon className="w-3.5 h-3.5" /> {s.label}
            <span className="text-white/40">({(data?.[s.key] || []).length})</span>
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search className="w-3.5 h-3.5 text-white/35 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} data-testid="spaces-search"
            placeholder="Rechercher par nom ou email…"
            className="w-full h-9 pl-8 pr-3 rounded-lg text-xs text-white placeholder-white/35 bg-white/[0.05] border border-white/15 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/50" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="spaces-status-filter"
          className="h-9 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15">
          <option value="ALL" className="bg-[#1F0A33]">Tous les statuts</option>
          {statuses.map((s) => <option key={s} value={s} className="bg-[#1F0A33]">{s}</option>)}
        </select>
        {(q || statusFilter !== 'ALL') && (
          <span className="text-[11px] text-white/45" data-testid="spaces-filter-count">{rows.length} résultat(s)</span>
        )}
      </div>
      {!data ? (
        <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-white/40" /></div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid={`spaces-table-${tab}`}>
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-white/40 border-b border-white/10">
                <th className="py-2 pr-3">Nom</th>
                <th className="py-2 pr-3">Email</th>
                <th className="py-2 pr-3">Pays</th>
                <th className="py-2 pr-3">Détail</th>
                <th className="py-2 pr-3">Compte</th>
                <th className="py-2 pr-3">Statut</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-white/40 text-xs">Aucune inscription pour le moment</td></tr>
              )}
              {rows.map((r) => {
                const suspended = ['SUSPENDED', 'REJECTED', 'CANCELLED'].includes(r.status);
                return (
                  <tr key={r.id} className="border-b border-white/5" data-testid={`spaces-row-${r.id}`}>
                    <td className="py-2.5 pr-3">
                      <button type="button" onClick={() => setDetailRow(r)} data-testid={`detail-${r.id}`}
                        className="text-white/90 font-medium hover:text-[#E9CF8E] underline-offset-2 hover:underline text-left">
                        {r.name}
                      </button>
                    </td>
                    <td className="py-2.5 pr-3 text-white/60">{r.email || '—'}</td>
                    <td className="py-2.5 pr-3 text-white/60">
                      {r.country ? (
                        <span className="inline-flex items-center gap-1.5">
                          <TerritoryFlag territory={r.country} className="w-4 h-auto rounded-[1px] inline-block" />{r.country}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-white/50 text-xs">{r.detail}</td>
                    <td className="py-2.5 pr-3">
                      {r.account_connected ? (
                        <span className="inline-flex items-center gap-1 text-emerald-300 text-xs"><Link2 className="w-3 h-3" /> Connecté</span>
                      ) : <span className="text-white/35 text-xs">Non lié</span>}
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusColor(r.status)}`}>{r.status}</span>
                    </td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-1.5">
                        <a href={space.route} target="_blank" rel="noreferrer" data-testid={`open-space-${r.id}`}
                          title="Ouvrir l'espace"
                          className="p-1.5 rounded-md bg-white/[0.05] border border-white/10 text-white/60 hover:text-white">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                        {tab === 'relays' && (
                          <button type="button" onClick={() => setManagerRow(r)} data-testid={`link-manager-${r.id}`}
                            title="Lier un gérant"
                            className="p-1.5 rounded-md bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/25">
                            <UserCog className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {suspended ? (
                          <button type="button" onClick={() => setStatus(r, space.active)} disabled={busy === r.id}
                            data-testid={`activate-${r.id}`} title="Réactiver"
                            className="p-1.5 rounded-md bg-emerald-500/15 border border-emerald-400/30 text-emerald-300 hover:bg-emerald-500/25">
                            {busy === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                          </button>
                        ) : (
                          <button type="button" onClick={() => setStatus(r, space.suspend)} disabled={busy === r.id}
                            data-testid={`suspend-${r.id}`} title="Suspendre"
                            className="p-1.5 rounded-md bg-red-500/15 border border-red-400/30 text-red-300 hover:bg-red-500/25">
                            {busy === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Ban className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <SpaceDetailDialog open={!!detailRow} onClose={() => setDetailRow(null)}
        kind={space.patchKind || space.key} row={detailRow} spaceLabel={space.label} />
      <RelayManagerDialog open={!!managerRow} onClose={() => setManagerRow(null)}
        relay={managerRow} onLinked={load} />
    </div>
  );
};
