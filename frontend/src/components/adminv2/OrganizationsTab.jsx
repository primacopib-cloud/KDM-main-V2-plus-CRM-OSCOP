import i18n from '@/i18n';
import { Building2 } from 'lucide-react';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { ORG_STATUSES, formatDate } from './adminV2Constants';

export const OrganizationsTab = ({
  organizations, orgStatusFilter, setOrgStatusFilter,
}) => (
          <TabsContent value="organizations">
            {/* Filter */}
            <div className="flex gap-3 mb-4">
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
            </div>

            {/* Organizations List */}
            <div className="glass-panel-soft rounded-[18px] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/[0.08]">
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.organisation')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.siret_2')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.territoire_2')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.statut')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.cree_le')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {organizations.map(org => {
                      const statusConfig = ORG_STATUSES[org.status] || ORG_STATUSES.DRAFT;
                      return (
                        <tr key={org.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                          <td className="p-4">
                            <p className="font-medium text-white/90">{org.legal_name}</p>
                          </td>
                          <td className="p-4 text-white/70 font-mono text-sm">{org.registration_id}</td>
                          <td className="p-4">
                            <Badge variant="outline" className="text-white/60 border-white/20">
                              {org.territory}
                            </Badge>
                          </td>
                          <td className="p-4">
                            <Badge className={statusConfig.color}>
                              {statusConfig.label}
                            </Badge>
                          </td>
                          <td className="p-4 text-white/50 text-sm">{formatDate(org.created_at)}</td>
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
          </TabsContent>
);
