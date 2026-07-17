import i18n from '@/i18n';
import {
  Building2, FileText, CheckCircle2, XCircle, ChevronDown, ChevronUp, MapPin,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../ui/collapsible';
import { APP_STATUSES, REJECTION_REASONS, formatDate } from './adminV2Constants';

export const ApplicationsTab = ({
  applications, appStatusFilter, setAppStatusFilter,
  expandedApp, setExpandedApp, openDecisionDialog,
}) => (
          <TabsContent value="applications">
            {/* Filter */}
            <div className="flex gap-3 mb-4">
              <Select value={appStatusFilter} onValueChange={setAppStatusFilter}>
                <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white">
                  <SelectValue placeholder={i18n.t('adm.filtrer_par_statut')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{i18n.t('adm.tous_les_statuts')}</SelectItem>
                  <SelectItem value="PENDING_REVIEW">{i18n.t('adm.en_revision')}</SelectItem>
                  <SelectItem value="SUBMITTED">{i18n.t('adm.soumis')}</SelectItem>
                  <SelectItem value="APPROVED">{i18n.t('adm.approuve')}</SelectItem>
                  <SelectItem value="REJECTED">{i18n.t('adm.rejete')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Applications List */}
            <div className="space-y-3">
              {applications.length === 0 ? (
                <div className="text-center py-12 text-white/50">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>{i18n.t('adm.aucune_demande')}</p>
                </div>
              ) : (
                applications.map(app => {
                  const statusConfig = APP_STATUSES[app.status] || APP_STATUSES.SUBMITTED;
                  const StatusIcon = statusConfig.icon;
                  const isExpanded = expandedApp === app.id;
                  const canDecide = ['SUBMITTED', 'PENDING_REVIEW'].includes(app.status);

                  return (
                    <Collapsible 
                      key={app.id}
                      open={isExpanded}
                      onOpenChange={() => setExpandedApp(isExpanded ? null : app.id)}
                    >
                      <div className="glass-panel-soft rounded-[18px] overflow-hidden">
                        <CollapsibleTrigger className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                          <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${statusConfig.color.split(' ')[0]}`}>
                              <StatusIcon className={`w-5 h-5 ${statusConfig.color.split(' ')[1]}`} />
                            </div>
                            <div className="text-left">
                              <p className="font-semibold text-white/90">{app.org?.legal_name || 'Organisation'}</p>
                              <p className="text-xs text-white/50">
                                {app.org?.registration_id} · {formatDate(app.created_at)}
                              </p>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-3">
                            <Badge className={statusConfig.color}>
                              {statusConfig.label}
                            </Badge>
                            {isExpanded ? (
                              <ChevronUp className="w-5 h-5 text-white/40" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-white/40" />
                            )}
                          </div>
                        </CollapsibleTrigger>

                        <CollapsibleContent>
                          <div className="px-4 pb-4 border-t border-white/[0.06] pt-4">
                            <div className="grid md:grid-cols-2 gap-6">
                              {/* Organization info */}
                              <div>
                                <h4 className="text-sm font-semibold text-white/70 mb-3">{i18n.t('adm.informations_entreprise')}</h4>
                                <div className="space-y-2 text-sm">
                                  <div className="flex items-center gap-2">
                                    <Building2 className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">{i18n.t('adm.raison_sociale')}</span>
                                    <span className="text-white/90">{app.org?.legal_name}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">{i18n.t('adm.siret')}</span>
                                    <span className="text-white/90">{app.org?.registration_id}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <MapPin className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">{i18n.t('adm.territoire')}</span>
                                    <span className="text-white/90">{app.org?.territory}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Documents */}
                              <div>
                                <h4 className="text-sm font-semibold text-white/70 mb-3">{i18n.t('adm.documents_fournis')}</h4>
                                {app.documents?.length > 0 ? (
                                  <div className="space-y-2">
                                    {app.documents.map((doc, idx) => (
                                      <div key={doc.id || `${doc.doc_type}-${idx}`} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02]">
                                        <FileText className="w-4 h-4 text-[#D4AF37]" />
                                        <span className="text-sm text-white/80">{doc.doc_type}</span>
                                        <Badge variant="outline" className="text-[10px] ml-auto">
                                          {doc.verified ? i18n.t('adm.verifie') : i18n.t('adm.non_verifie')}
                                        </Badge>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-sm text-white/50">{i18n.t('adm.aucun_document')}</p>
                                )}
                              </div>
                            </div>

                            {/* Actions */}
                            {canDecide && (
                              <div className="mt-4 pt-4 border-t border-white/[0.06] flex gap-3 justify-end">
                                <Button
                                  variant="outline"
                                  onClick={() => openDecisionDialog(app, 'REJECTED')}
                                  className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                                >
                                  <XCircle className="w-4 h-4 mr-2" />
                                  Rejeter
                                </Button>
                                <Button
                                  onClick={() => openDecisionDialog(app, 'APPROVED')}
                                  className="bg-green-500 hover:bg-green-600 text-white"
                                >
                                  <CheckCircle2 className="w-4 h-4 mr-2" />
                                  Approuver
                                </Button>
                              </div>
                            )}

                            {/* Decision info if already decided */}
                            {app.status === 'REJECTED' && app.reason_code && (
                              <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                <p className="text-sm text-red-400">
                                  <strong>{i18n.t('adm.raison_du_rejet')}</strong> {REJECTION_REASONS.find(r => r.code === app.reason_code)?.label || app.reason_code}
                                </p>
                                {app.comment && (
                                  <p className="text-sm text-red-400/80 mt-1">{app.comment}</p>
                                )}
                              </div>
                            )}
                          </div>
                        </CollapsibleContent>
                      </div>
                    </Collapsible>
                  );
                })
              )}
            </div>
          </TabsContent>
);
