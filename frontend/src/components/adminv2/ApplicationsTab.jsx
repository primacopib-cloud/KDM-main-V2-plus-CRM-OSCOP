import i18n from '@/i18n';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Building2, FileText, CheckCircle2, XCircle, ChevronDown, ChevronUp, MapPin, Search, Download, Send, Loader2, BellRing,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../ui/collapsible';
import { APP_STATUSES, REJECTION_REASONS, formatDate } from './adminV2Constants';
import { DocPreviewModal } from './DocPreviewModal';
import { applicationsAPIV2 } from '../../services/api';

const exportCsv = (apps) => {
  const header = ['Raison sociale', 'SIRET', 'Territoire', 'Statut', 'Contact', 'Email', 'Créée le', 'Relancée le', 'Documents'];
  const rows = apps.map((a) => [
    a.org?.legal_name, a.org?.registration_id, a.org?.territory, a.status,
    a.org?.contact_name, a.org?.contact_email,
    formatDate(a.created_at), a.reminder_sent_at ? formatDate(a.reminder_sent_at) : '',
    (a.documents || []).length,
  ]);
  const csv = [header, ...rows]
    .map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(';'))
    .join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `demandes-adhesion-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
};

export const ApplicationsTab = ({
  applications, appStatusFilter, setAppStatusFilter,
  expandedApp, setExpandedApp, openDecisionDialog,
}) => {
  const [search, setSearch] = useState('');
  const [previewDoc, setPreviewDoc] = useState(null);
  const [remindingId, setRemindingId] = useState(null);
  const [remindedNow, setRemindedNow] = useState({});

  const handleRemind = async (app) => {
    setRemindingId(app.id);
    try {
      const r = await applicationsAPIV2.remindNow(app.id);
      if (r.reminders_sent > 0) {
        toast.success(i18n.t('adm.relance_envoyee', 'Relance envoyée par email'));
        setRemindedNow((p) => ({ ...p, [app.id]: new Date().toISOString() }));
      } else {
        toast.info(i18n.t('adm.relance_aucun_email', "Aucun email envoyé (contact introuvable)"));
      }
    } catch (e) {
      toast.error(e.message || 'Erreur');
    } finally {
      setRemindingId(null);
    }
  };

  const q = search.trim().toLowerCase();
  const filtered = (appStatusFilter === 'all'
    ? applications
    : applications.filter((a) =>
        appStatusFilter === 'PENDING_REVIEW'
          ? ['PENDING_REVIEW', 'SUBMITTED'].includes(a.status)
          : a.status === appStatusFilter
      )
  ).filter((a) => !q
    || (a.org?.legal_name || '').toLowerCase().includes(q)
    || (a.org?.registration_id || '').toLowerCase().includes(q));
  return (
          <TabsContent value="applications">
            {/* Filter + Search */}
            <div className="flex flex-col sm:flex-row gap-3 mb-4">
              <Select value={appStatusFilter} onValueChange={setAppStatusFilter}>
                <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white" data-testid="admin-app-status-filter">
                  <SelectValue placeholder={i18n.t('adm.filtrer_par_statut')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{i18n.t('adm.tous_les_statuts')}</SelectItem>
                  <SelectItem value="DRAFT">{i18n.t('adm.brouillon')}</SelectItem>
                  <SelectItem value="PENDING_REVIEW">{i18n.t('adm.en_revision')}</SelectItem>
                  <SelectItem value="APPROVED">{i18n.t('adm.approuve')}</SelectItem>
                  <SelectItem value="REJECTED">{i18n.t('adm.rejete')}</SelectItem>
                </SelectContent>
              </Select>
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={i18n.t('adm.recherche_raison_siret', 'Rechercher par raison sociale ou SIRET…')}
                  className="pl-9 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40"
                  data-testid="admin-app-search-input"
                />
              </div>
              <Button
                variant="outline"
                onClick={() => exportCsv(filtered)}
                disabled={filtered.length === 0}
                className="border-white/15 text-white/80 hover:bg-white/[0.06]"
                data-testid="admin-app-export-csv"
              >
                <Download className="w-4 h-4 mr-2" />
                {i18n.t('adm.exporter_csv', 'Exporter CSV')} ({filtered.length})
              </Button>
            </div>

            {/* Applications List */}
            <div className="space-y-3">
              {filtered.length === 0 ? (
                <div className="text-center py-12 text-white/50">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>{i18n.t('adm.aucune_demande')}</p>
                </div>
              ) : (
                filtered.map(app => {
                  const statusConfig = APP_STATUSES[app.status] || APP_STATUSES.SUBMITTED;
                  const StatusIcon = statusConfig.icon;
                  const isExpanded = expandedApp === app.id;
                  const canDecide = ['SUBMITTED', 'PENDING_REVIEW'].includes(app.status);
                  const remindedAt = remindedNow[app.id] || app.reminder2_sent_at || app.reminder_sent_at;
                  const remindCount = (app.reminder_sent_at ? 1 : 0) + (app.reminder2_sent_at ? 1 : 0) + (remindedNow[app.id] ? 1 : 0);

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
                            {remindedAt && (
                              <Badge className="bg-orange-500/15 text-orange-300 border-0 hidden sm:inline-flex items-center gap-1" data-testid={`app-reminded-badge-${app.id}`}>
                                <BellRing className="w-3 h-3" />
                                {remindCount > 1 ? `${remindCount}× · ` : ''}{i18n.t('adm.relance_le', 'Relancé le')} {formatDate(remindedAt)}
                              </Badge>
                            )}
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
                                  {app.org?.legal_form && (
                                    <div className="flex items-center gap-2">
                                      <FileText className="w-4 h-4 text-white/40" />
                                      <span className="text-white/60">Statut juridique</span>
                                      <span className="text-white/90">{app.org.legal_form}</span>
                                    </div>
                                  )}
                                  {app.org?.contact_email && (
                                    <div className="flex items-center gap-2">
                                      <Building2 className="w-4 h-4 text-white/40" />
                                      <span className="text-white/60">Contact</span>
                                      <span className="text-white/90">{app.org.contact_name} · {app.org.contact_email}{app.org.contact_phone ? ` · ${app.org.contact_phone}` : ''}</span>
                                    </div>
                                  )}
                                  {(app.org?.address || app.org?.city) && (
                                    <div className="flex items-center gap-2">
                                      <MapPin className="w-4 h-4 text-white/40" />
                                      <span className="text-white/60">Adresse</span>
                                      <span className="text-white/90">
                                        {[app.org.address, [app.org.postal_code, app.org.city].filter(Boolean).join(' ')].filter(Boolean).join(', ')}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Documents */}
                              <div>
                                <h4 className="text-sm font-semibold text-white/70 mb-3">{i18n.t('adm.documents_fournis')}</h4>
                                {app.documents?.length > 0 ? (
                                  <div className="space-y-2">
                                    {app.documents.map((doc, idx) => {
                                      const isRealFile = (doc.file_url || '').startsWith('/api');
                                      const inner = (
                                        <>
                                          <FileText className="w-4 h-4 text-[#D4AF37]" />
                                          <span className="text-sm text-white/80">{doc.doc_type}</span>
                                          {doc.file_name && <span className="text-xs text-white/50 truncate max-w-[140px]">{doc.file_name}</span>}
                                          <Badge variant="outline" className="text-[10px] ml-auto">
                                            {isRealFile ? i18n.t('adm.consulter', 'Consulter') : (doc.verified ? i18n.t('adm.verifie') : i18n.t('adm.non_verifie'))}
                                          </Badge>
                                        </>
                                      );
                                      return isRealFile ? (
                                        <button key={doc.id || `${doc.doc_type}-${idx}`} type="button"
                                          onClick={() => setPreviewDoc(doc)}
                                          data-testid={`admin-doc-link-${doc.doc_type}`}
                                          className="w-full flex items-center gap-2 p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.06] transition-colors cursor-pointer text-left">
                                          {inner}
                                        </button>
                                      ) : (
                                        <div key={doc.id || `${doc.doc_type}-${idx}`} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02]">
                                          {inner}
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <p className="text-sm text-white/50">{i18n.t('adm.aucun_document')}</p>
                                )}
                              </div>
                            </div>

                            {/* Actions */}
                            {app.status === 'DRAFT' && (
                              <div className="mt-4 pt-4 border-t border-white/[0.06] flex items-center justify-between gap-3 flex-wrap">
                                <p className="text-xs text-white/50">
                                  {remindedAt
                                    ? `${i18n.t('adm.relance_le', 'Relancé le')} ${formatDate(remindedAt)}`
                                    : i18n.t('adm.jamais_relance', 'Jamais relancé')}
                                </p>
                                <Button
                                  variant="outline"
                                  onClick={() => handleRemind(app)}
                                  disabled={remindingId === app.id}
                                  className="border-orange-500/30 text-orange-300 hover:bg-orange-500/10"
                                  data-testid={`remind-now-btn-${app.id}`}
                                >
                                  {remindingId === app.id
                                    ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    : <Send className="w-4 h-4 mr-2" />}
                                  {i18n.t('adm.relancer_maintenant', 'Relancer maintenant')}
                                </Button>
                              </div>
                            )}
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
            <DocPreviewModal doc={previewDoc} onClose={() => setPreviewDoc(null)} />
          </TabsContent>
  );
};
