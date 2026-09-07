import i18n from '@/i18n';
import { useState } from 'react';
import { toast } from 'sonner';
import { Building2, Plus, Pencil, Trash2, Eye, EyeOff, Loader2 } from 'lucide-react';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { adminAPIV2 } from '../../services/api';
import { ORG_STATUSES, formatDate } from './adminV2Constants';
import { OrgFormDialog } from './OrgFormDialog';
import { TerritoryFlag } from '../Flag';

const iconBtn = 'p-1.5 rounded-lg border transition-colors';

export const OrganizationsTab = ({
  organizations, orgStatusFilter, setOrgStatusFilter, reload,
}) => {
  const [selected, setSelected] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState(null);
  const [busy, setBusy] = useState(false);

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  const allSelected = organizations.length > 0 && selected.length === organizations.length;
  const toggleAll = () => setSelected(allSelected ? [] : organizations.map((o) => o.id));

  const run = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); setSelected([]); reload(); }
    catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const deleteOne = (org) => {
    if (!window.confirm(`Supprimer définitivement « ${org.legal_name} » ?`)) return;
    run(() => adminAPIV2.deleteOrg(org.id), 'Organisation supprimée');
  };

  const toggleHidden = (org) => {
    run(() => adminAPIV2.setOrgVisibility(org.id, !org.hidden), org.hidden ? 'Organisation affichée' : 'Organisation masquée');
  };

  const bulk = (action, label) => {
    if (action === 'delete' && !window.confirm(`Supprimer définitivement ${selected.length} organisation(s) ?`)) return;
    run(() => adminAPIV2.bulkOrgs(action, selected), `${label} : ${selected.length} organisation(s)`);
  };

  return (
    <TabsContent value="organizations">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <Select value={orgStatusFilter} onValueChange={setOrgStatusFilter}>
          <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white">
            <SelectValue placeholder={i18n.t('adm.filtrer_par_statut')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{i18n.t('adm.tous_les_statuts')}</SelectItem>
            <SelectItem value="APPROVED">{i18n.t('adm.approuve')}</SelectItem>
            <SelectItem value="PENDING_REVIEW">{i18n.t('adm.en_revision')}</SelectItem>
            <SelectItem value="SUSPENDED">{i18n.t('adm.suspendu')}</SelectItem>
          </SelectContent>
        </Select>
        <button type="button" data-testid="new-org-btn"
          onClick={() => { setEditingOrg(null); setDialogOpen(true); }}
          className="inline-flex items-center gap-1.5 h-10 px-4 rounded-lg text-sm font-semibold bg-[#D9B35A] text-black hover:bg-[#c5a04b] transition-colors">
          <Plus size={15} /> Nouvelle organisation
        </button>
        {selected.length > 0 && (
          <div className="flex items-center gap-2 ml-auto" data-testid="org-bulk-bar">
            <span className="text-xs text-white/60">{selected.length} sélectionnée(s)</span>
            <button type="button" disabled={busy} onClick={() => bulk('hide', 'Masquées')} data-testid="bulk-hide-btn"
              className="h-9 px-3 rounded-lg text-xs font-bold bg-white/10 text-white/80 hover:bg-white/15 inline-flex items-center gap-1.5">
              <EyeOff size={13} /> Masquer
            </button>
            <button type="button" disabled={busy} onClick={() => bulk('show', 'Affichées')} data-testid="bulk-show-btn"
              className="h-9 px-3 rounded-lg text-xs font-bold bg-white/10 text-white/80 hover:bg-white/15 inline-flex items-center gap-1.5">
              <Eye size={13} /> Afficher
            </button>
            <button type="button" disabled={busy} onClick={() => bulk('suspend', 'Suspendues')} data-testid="bulk-suspend-btn"
              className="h-9 px-3 rounded-lg text-xs font-bold bg-orange-500/15 text-orange-300 border border-orange-500/30 hover:bg-orange-500/25">
              Suspendre
            </button>
            <button type="button" disabled={busy} onClick={() => bulk('delete', 'Supprimées')} data-testid="bulk-delete-btn"
              className="h-9 px-3 rounded-lg text-xs font-bold bg-red-500/15 text-red-300 border border-red-500/30 hover:bg-red-500/25 inline-flex items-center gap-1.5">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />} Supprimer
            </button>
          </div>
        )}
      </div>

      <div className="glass-panel-soft rounded-[18px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.08]">
                <th className="p-4 w-10">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} data-testid="org-select-all"
                    className="accent-[#D9B35A] w-4 h-4 cursor-pointer" />
                </th>
                <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.organisation')}</th>
                <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.siret_2')}</th>
                <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.territoire_2')}</th>
                <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.statut')}</th>
                <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.cree_le')}</th>
                <th className="text-right p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {organizations.map((org) => {
                const statusConfig = ORG_STATUSES[org.status] || ORG_STATUSES.DRAFT;
                return (
                  <tr key={org.id} data-testid={`org-row-${org.id}`}
                    className={`border-b border-white/[0.04] hover:bg-white/[0.02] ${org.hidden ? 'opacity-45' : ''}`}>
                    <td className="p-4">
                      <input type="checkbox" checked={selected.includes(org.id)} onChange={() => toggle(org.id)}
                        data-testid={`org-check-${org.id}`} className="accent-[#D9B35A] w-4 h-4 cursor-pointer" />
                    </td>
                    <td className="p-4">
                      <p className="font-medium text-white/90 m-0">{org.legal_name}</p>
                      {org.hidden && (
                        <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded-full bg-white/10 text-white/60 border border-white/20"
                          data-testid={`org-hidden-badge-${org.id}`}>Masquée</span>
                      )}
                    </td>
                    <td className="p-4 text-white/70 font-mono text-sm">{org.registration_id}</td>
                    <td className="p-4">
                      <Badge variant="outline" className="text-white/60 border-white/20 gap-1.5"><TerritoryFlag territory={org.territory} className="w-3.5 h-auto rounded-[1px] inline-block" />{org.territory}</Badge>
                    </td>
                    <td className="p-4"><Badge className={statusConfig.color}>{statusConfig.label}</Badge></td>
                    <td className="p-4 text-white/50 text-sm">{formatDate(org.created_at)}</td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-1.5">
                        <button type="button" title="Modifier" data-testid={`org-edit-${org.id}`}
                          onClick={() => { setEditingOrg(org); setDialogOpen(true); }}
                          className={`${iconBtn} bg-[#D9B35A]/10 border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/20`}>
                          <Pencil size={13} />
                        </button>
                        <button type="button" title={org.hidden ? 'Afficher' : 'Masquer'} data-testid={`org-toggle-hidden-${org.id}`}
                          onClick={() => toggleHidden(org)}
                          className={`${iconBtn} bg-white/[0.05] border-white/15 text-white/60 hover:bg-white/10`}>
                          {org.hidden ? <Eye size={13} /> : <EyeOff size={13} />}
                        </button>
                        <button type="button" title="Supprimer" data-testid={`org-delete-${org.id}`}
                          onClick={() => deleteOne(org)}
                          className={`${iconBtn} bg-red-500/10 border-red-500/25 text-red-400 hover:bg-red-500/20`}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {organizations.length === 0 && (
          <div className="text-center py-12 text-white/50">
            <Building2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{i18n.t('adm.aucune_organisation')}</p>
          </div>
        )}
      </div>

      <OrgFormDialog open={dialogOpen} onClose={() => setDialogOpen(false)} org={editingOrg} onSaved={reload} />
    </TabsContent>
  );
};
