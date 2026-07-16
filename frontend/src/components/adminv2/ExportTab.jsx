import i18n from '@/i18n';
import { Calendar, Download, Filter, Loader2, Building2, FileText, Package, Wallet, Eye, Users } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '../ui/popover';

export const ExportTab = ({
  applications, organizations, exportSummary, exportLoading,
  exportFilters, setExportFilters, showFilters, setShowFilters,
  handleExportDownload, clearExportFilters,
}) => {
  const hasActiveFilters = exportFilters.dateFrom || exportFilters.dateTo || exportFilters.statusFilter;
  return (
          <TabsContent value="export">
            <div className="glass-panel-soft rounded-[18px] p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/10 flex items-center justify-center">
                    <Download className="w-5 h-5 text-[#D9B35A]" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{i18n.t('adm.export_des_donnees')}</h3>
                    <p className="text-sm text-white/50">{i18n.t('adm.telechargez_les_donnees_au_format')}</p>
                  </div>
                </div>
                
                {/* Filters Toggle */}
                <Popover open={showFilters} onOpenChange={setShowFilters}>
                  <PopoverTrigger asChild>
                    <Button 
                      variant="outline" 
                      className={`border-white/10 ${hasActiveFilters ? 'bg-[#D9B35A]/10 border-[#D9B35A]/30' : ''}`}
                      data-testid="export-filters-btn"
                    >
                      <Filter className={`w-4 h-4 mr-2 ${hasActiveFilters ? 'text-[#D9B35A]' : ''}`} />
                      Filtres
                      {hasActiveFilters && (
                        <Badge className="ml-2 bg-[#D9B35A] text-black text-xs px-1.5">
                          {[exportFilters.dateFrom, exportFilters.dateTo, exportFilters.statusFilter].filter(Boolean).length}
                        </Badge>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 bg-[#0a0d14] border-white/10 text-white" align="end">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-sm">{i18n.t('adm.filtres_d_export')}</h4>
                        {hasActiveFilters && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearExportFilters}
                            className="h-auto p-1 text-xs text-white/50 hover:text-white"
                          >
                            <X className="w-3 h-3 mr-1" />
                            {i18n.t('adm.reinitialiser')}
                          </Button>
                        )}
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">{i18n.t('adm.date_de_debut')}</Label>
                        <Input
                          type="date"
                          value={exportFilters.dateFrom}
                          onChange={(e) => setExportFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                          className="bg-white/[0.04] border-white/10 text-white [color-scheme:dark]"
                          data-testid="export-date-from"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">{i18n.t('adm.date_de_fin')}</Label>
                        <Input
                          type="date"
                          value={exportFilters.dateTo}
                          onChange={(e) => setExportFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                          className="bg-white/[0.04] border-white/10 text-white [color-scheme:dark]"
                          data-testid="export-date-to"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">{i18n.t('adm.statut')}</Label>
                        <Select 
                          value={exportFilters.statusFilter} 
                          onValueChange={(value) => setExportFilters(prev => ({ ...prev, statusFilter: value === 'all' ? '' : value }))}
                        >
                          <SelectTrigger className="bg-white/[0.04] border-white/10 text-white" data-testid="export-status-filter">
                            <SelectValue placeholder={i18n.t('adm.tous_les_statuts')} />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">{i18n.t('adm.tous_les_statuts')}</SelectItem>
                            <SelectItem value="DRAFT">{i18n.t('adm.brouillon')}</SelectItem>
                            <SelectItem value="SUBMITTED">{i18n.t('adm.soumis')}</SelectItem>
                            <SelectItem value="PENDING_REVIEW">{i18n.t('adm.en_revision')}</SelectItem>
                            <SelectItem value="APPROVED">{i18n.t('adm.approuve')}</SelectItem>
                            <SelectItem value="REJECTED">{i18n.t('adm.rejete')}</SelectItem>
                            <SelectItem value="SUSPENDED">{i18n.t('adm.suspendu')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="pt-2 border-t border-white/[0.08]">
                        <p className="text-xs text-white/40">
                          {i18n.t('adm.filtres_s_appliquent')}
                        </p>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>
              
              {/* Active Filters Display */}
              {hasActiveFilters && (
                <div className="mb-4 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-white/50">{i18n.t('adm.filtres_actifs')}</span>
                  {exportFilters.dateFrom && (
                    <Badge variant="outline" className="text-xs border-[#D9B35A]/30 text-[#D9B35A]">
                      <Calendar className="w-3 h-3 mr-1" />
                      Depuis: {exportFilters.dateFrom}
                    </Badge>
                  )}
                  {exportFilters.dateTo && (
                    <Badge variant="outline" className="text-xs border-[#D9B35A]/30 text-[#D9B35A]">
                      <Calendar className="w-3 h-3 mr-1" />
                      {i18n.t('adm.jusqu_a')} {exportFilters.dateTo}
                    </Badge>
                  )}
                  {exportFilters.statusFilter && (
                    <Badge variant="outline" className="text-xs border-[#D9B35A]/30 text-[#D9B35A]">
                      Statut: {exportFilters.statusFilter}
                    </Badge>
                  )}
                </div>
              )}

              {exportSummary ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {exportSummary.exports_available.map((exp) => {
                    const icons = {
                      organizations: Building2,
                      applications: FileText,
                      orders: Package,
                      transactions: Wallet,
                      audit_log: Eye,
                      products: Package,
                      users: Users,
                    };
                    const Icon = icons[exp.type] || FileText;

                    return (
                      <div 
                        key={exp.type}
                        className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                              <Icon className="w-4 h-4 text-white/60" />
                            </div>
                            <div>
                              <p className="font-medium text-white/90">{exp.label}</p>
                              <p className="text-xs text-white/40">{exp.count} {i18n.t('adm.entrees')}</p>
                            </div>
                          </div>
                        </div>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExportDownload(exp.type)}
                          disabled={exportLoading[exp.type] || exp.count === 0}
                          className="w-full border-white/10 hover:bg-white/[0.04]"
                          data-testid={`export-${exp.type}-btn`}
                        >
                          {exportLoading[exp.type] ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Export en cours...
                            </>
                          ) : (
                            <>
                              <Download className="w-4 h-4 mr-2" />
                              {i18n.t('adm.telecharger_csv')}
                            </>
                          )}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-white/50">
                  <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin" />
                  <p>{i18n.t('adm.chargement_des_options_d_export')}</p>
                </div>
              )}

              <div className="mt-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                <p className="text-sm text-blue-400">
                  <strong>{i18n.t('adm.note')}</strong> {i18n.t('adm.csv_note_desc')}
                </p>
              </div>
            </div>
          </TabsContent>
);
};
