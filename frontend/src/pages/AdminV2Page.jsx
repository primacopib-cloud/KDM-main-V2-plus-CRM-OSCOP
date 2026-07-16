import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, Shield, Building2, Users, FileText, Clock, CheckCircle2,
  XCircle, AlertCircle, Eye, Loader2, ChevronDown, ChevronUp, Search,
  MapPin, Calendar, Mail, Phone, Wallet, TrendingUp, Package, Download,
  Filter, X
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../components/ui/collapsible';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '../components/ui/popover';

import { partners } from '../data/mock';
import { authAPI, applicationsAPIV2, adminAPIV2, exportAPI } from '../services/api';
import NotificationsDropdown from '../components/NotificationsDropdown';

// Application status configuration
const APP_STATUSES = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400', icon: FileText },
  SUBMITTED: { label: 'Soumis', color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  PENDING_REVIEW: { label: 'En révision', color: 'bg-blue-500/20 text-blue-400', icon: Eye },
  APPROVED: { label: 'Approuvé', color: 'bg-green-500/20 text-green-400', icon: CheckCircle2 },
  REJECTED: { label: 'Rejeté', color: 'bg-red-500/20 text-red-400', icon: XCircle },
};

// Org status configuration
const ORG_STATUSES = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400' },
  SUBMITTED: { label: 'Soumis', color: 'bg-yellow-500/20 text-yellow-400' },
  PENDING_REVIEW: { label: 'En révision', color: 'bg-blue-500/20 text-blue-400' },
  APPROVED: { label: 'Approuvé', color: 'bg-green-500/20 text-green-400' },
  REJECTED: { label: 'Rejeté', color: 'bg-red-500/20 text-red-400' },
  SUSPENDED: { label: 'Suspendu', color: 'bg-orange-500/20 text-orange-400' },
  CLOSED: { label: 'Fermé', color: 'bg-gray-500/20 text-gray-400' },
};

// Rejection reasons
const REJECTION_REASONS = [
  { code: 'INCOMPLETE_DOCS', label: 'Documents incomplets ou illisibles' },
  { code: 'INVALID_REGISTRATION', label: 'Numéro d\'immatriculation invalide' },
  { code: 'INELIGIBLE_ACTIVITY', label: 'Activité non éligible' },
  { code: 'DUPLICATE', label: 'Demande en doublon' },
  { code: 'FRAUD_SUSPICION', label: 'Suspicion de fraude' },
  { code: 'OTHER', label: 'Autre raison' },
];

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  const date = new Date(dateStr);
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function AdminV2Page() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('applications');
  
  // Applications data
  const [applications, setApplications] = useState([]);
  const [appStatusFilter, setAppStatusFilter] = useState('PENDING_REVIEW');
  const [expandedApp, setExpandedApp] = useState(null);
  
  // Organizations data
  const [organizations, setOrganizations] = useState([]);
  const [orgStatusFilter, setOrgStatusFilter] = useState('all');
  
  // Decision dialog
  const [decisionDialogOpen, setDecisionDialogOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);
  const [decisionType, setDecisionType] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [decisionComment, setDecisionComment] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);
  
  // Export data
  const [exportSummary, setExportSummary] = useState(null);
  const [exportLoading, setExportLoading] = useState({});
  
  // Export filters
  const [exportFilters, setExportFilters] = useState({
    dateFrom: '',
    dateTo: '',
    statusFilter: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  // Load data
  useEffect(() => {
    const init = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion');
        return;
      }

      try {
        const userData = await authAPI.getMe();
        if (!userData.is_admin) {
          toast.error('Accès réservé aux administrateurs');
          navigate('/dashboard');
          return;
        }

        // Load applications and orgs
        await loadData();

      } catch (error) {
        console.error('Init error:', error);
        toast.error('Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  const loadData = async () => {
    try {
      const [appsData, orgsData, exportData] = await Promise.all([
        applicationsAPIV2.listAdmin(appStatusFilter === 'all' ? null : appStatusFilter),
        adminAPIV2.listOrgs(orgStatusFilter === 'all' ? null : orgStatusFilter),
        exportAPI.getSummary().catch(() => null),
      ]);
      setApplications(appsData);
      setOrganizations(orgsData);
      if (exportData) setExportSummary(exportData);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  // Reload when filters change
  useEffect(() => {
    if (!loading) {
      loadData();
    }
  }, [appStatusFilter, orgStatusFilter]);

  // Handle decision
  const handleDecision = async () => {
    if (!selectedApp || !decisionType) return;

    if (decisionType === 'REJECTED' && !rejectionReason) {
      toast.error('Veuillez sélectionner une raison de rejet');
      return;
    }

    setSubmittingDecision(true);
    try {
      await applicationsAPIV2.decide(
        selectedApp.id,
        decisionType,
        decisionType === 'REJECTED' ? rejectionReason : null,
        decisionComment || null
      );

      toast.success(decisionType === 'APPROVED' ? 'Demande approuvée' : 'Demande rejetée');
      
      // Update local state
      setApplications(prev => prev.map(app => 
        app.id === selectedApp.id ? { ...app, status: decisionType } : app
      ));
      
      setDecisionDialogOpen(false);
      setSelectedApp(null);
      setDecisionType('');
      setRejectionReason('');
      setDecisionComment('');

      // Reload to get updated org status
      loadData();

    } catch (error) {
      toast.error(error.message || 'Erreur lors de la décision');
    } finally {
      setSubmittingDecision(false);
    }
  };

  // Open decision dialog
  const openDecisionDialog = (app, type) => {
    setSelectedApp(app);
    setDecisionType(type);
    setDecisionDialogOpen(true);
  };

  // Handle export download
  const handleExportDownload = async (exportType) => {
    setExportLoading(prev => ({ ...prev, [exportType]: true }));
    try {
      await exportAPI.download(exportType, {
        dateFrom: exportFilters.dateFrom || null,
        dateTo: exportFilters.dateTo || null,
        statusFilter: exportFilters.statusFilter || null,
      });
      toast.success(`Export ${exportType} téléchargé`);
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'export');
    } finally {
      setExportLoading(prev => ({ ...prev, [exportType]: false }));
    }
  };

  // Clear export filters
  const clearExportFilters = () => {
    setExportFilters({
      dateFrom: '',
      dateTo: '',
      statusFilter: '',
    });
  };

  // Check if filters are active
  const hasActiveFilters = exportFilters.dateFrom || exportFilters.dateTo || exportFilters.statusFilter;

  // Stats
  const appStats = {
    total: applications.length,
    pending: applications.filter(a => a.status === 'PENDING_REVIEW').length,
    approved: applications.filter(a => a.status === 'APPROVED').length,
    rejected: applications.filter(a => a.status === 'REJECTED').length,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="admin-v2-page">
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.86)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Retour</span>
            </Link>
            <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
              <Shield className="w-3 h-3 mr-1" />
              Admin V2
            </Badge>
          </div>
          
          <div className="flex items-center gap-3">
            <NotificationsDropdown isAdmin={true} />
            <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-10 w-auto object-contain" />
            <img src={partners.oscop.logo} alt="O'SCOP" className="h-8 w-auto object-contain" />
          </div>
        </div>
      </header>

      <div className="max-w-[1280px] mx-auto px-5 py-6">
        {/* Title */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1">Administration B2B</h1>
          <p className="text-white/60 text-sm">Gestion des demandes d'adhésion et des organisations</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-white/50" />
              <p className="text-xs text-white/50">Total demandes</p>
            </div>
            <p className="text-2xl font-bold">{appStats.total}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-yellow-400" />
              <p className="text-xs text-white/50">En attente</p>
            </div>
            <p className="text-2xl font-bold text-yellow-400">{appStats.pending}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <p className="text-xs text-white/50">Approuvées</p>
            </div>
            <p className="text-2xl font-bold text-green-400">{appStats.approved}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <p className="text-xs text-white/50">Rejetées</p>
            </div>
            <p className="text-2xl font-bold text-red-400">{appStats.rejected}</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 mb-6">
            <TabsTrigger 
              value="applications"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              <FileText className="w-4 h-4 mr-2" />
              Demandes d'adhésion
            </TabsTrigger>
            <TabsTrigger 
              value="organizations"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              <Building2 className="w-4 h-4 mr-2" />
              Organisations
            </TabsTrigger>
            <TabsTrigger 
              value="export"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </TabsTrigger>
          </TabsList>

          {/* Applications Tab */}
          <TabsContent value="applications">
            {/* Filter */}
            <div className="flex gap-3 mb-4">
              <Select value={appStatusFilter} onValueChange={setAppStatusFilter}>
                <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white">
                  <SelectValue placeholder="Filtrer par statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="PENDING_REVIEW">En révision</SelectItem>
                  <SelectItem value="SUBMITTED">Soumis</SelectItem>
                  <SelectItem value="APPROVED">Approuvé</SelectItem>
                  <SelectItem value="REJECTED">Rejeté</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Applications List */}
            <div className="space-y-3">
              {applications.length === 0 ? (
                <div className="text-center py-12 text-white/50">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Aucune demande</p>
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
                                <h4 className="text-sm font-semibold text-white/70 mb-3">Informations entreprise</h4>
                                <div className="space-y-2 text-sm">
                                  <div className="flex items-center gap-2">
                                    <Building2 className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">Raison sociale:</span>
                                    <span className="text-white/90">{app.org?.legal_name}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">SIRET:</span>
                                    <span className="text-white/90">{app.org?.registration_id}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <MapPin className="w-4 h-4 text-white/40" />
                                    <span className="text-white/60">Territoire:</span>
                                    <span className="text-white/90">{app.org?.territory}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Documents */}
                              <div>
                                <h4 className="text-sm font-semibold text-white/70 mb-3">Documents fournis</h4>
                                {app.documents?.length > 0 ? (
                                  <div className="space-y-2">
                                    {app.documents.map((doc, idx) => (
                                      <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02]">
                                        <FileText className="w-4 h-4 text-[#D4AF37]" />
                                        <span className="text-sm text-white/80">{doc.doc_type}</span>
                                        <Badge variant="outline" className="text-[10px] ml-auto">
                                          {doc.verified ? 'Vérifié' : 'Non vérifié'}
                                        </Badge>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-sm text-white/50">Aucun document</p>
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
                                  <strong>Raison du rejet:</strong> {REJECTION_REASONS.find(r => r.code === app.reason_code)?.label || app.reason_code}
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

          {/* Organizations Tab */}
          <TabsContent value="organizations">
            {/* Filter */}
            <div className="flex gap-3 mb-4">
              <Select value={orgStatusFilter} onValueChange={setOrgStatusFilter}>
                <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white">
                  <SelectValue placeholder="Filtrer par statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="APPROVED">Approuvé</SelectItem>
                  <SelectItem value="PENDING_REVIEW">En révision</SelectItem>
                  <SelectItem value="SUSPENDED">Suspendu</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Organizations List */}
            <div className="glass-panel-soft rounded-[18px] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/[0.08]">
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">Organisation</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">SIRET</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">Territoire</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">Statut</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">Créé le</th>
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
                  <p>Aucune organisation</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Export Tab */}
          <TabsContent value="export">
            <div className="glass-panel-soft rounded-[18px] p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/10 flex items-center justify-center">
                    <Download className="w-5 h-5 text-[#D9B35A]" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Export des données</h3>
                    <p className="text-sm text-white/50">Téléchargez les données au format CSV (Excel compatible)</p>
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
                        <h4 className="font-semibold text-sm">Filtres d'export</h4>
                        {hasActiveFilters && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearExportFilters}
                            className="h-auto p-1 text-xs text-white/50 hover:text-white"
                          >
                            <X className="w-3 h-3 mr-1" />
                            Réinitialiser
                          </Button>
                        )}
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">Date de début</Label>
                        <Input
                          type="date"
                          value={exportFilters.dateFrom}
                          onChange={(e) => setExportFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                          className="bg-white/[0.04] border-white/10 text-white [color-scheme:dark]"
                          data-testid="export-date-from"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">Date de fin</Label>
                        <Input
                          type="date"
                          value={exportFilters.dateTo}
                          onChange={(e) => setExportFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                          className="bg-white/[0.04] border-white/10 text-white [color-scheme:dark]"
                          data-testid="export-date-to"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label className="text-xs text-white/60">Statut</Label>
                        <Select 
                          value={exportFilters.statusFilter} 
                          onValueChange={(value) => setExportFilters(prev => ({ ...prev, statusFilter: value === 'all' ? '' : value }))}
                        >
                          <SelectTrigger className="bg-white/[0.04] border-white/10 text-white" data-testid="export-status-filter">
                            <SelectValue placeholder="Tous les statuts" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">Tous les statuts</SelectItem>
                            <SelectItem value="DRAFT">Brouillon</SelectItem>
                            <SelectItem value="SUBMITTED">Soumis</SelectItem>
                            <SelectItem value="PENDING_REVIEW">En révision</SelectItem>
                            <SelectItem value="APPROVED">Approuvé</SelectItem>
                            <SelectItem value="REJECTED">Rejeté</SelectItem>
                            <SelectItem value="SUSPENDED">Suspendu</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="pt-2 border-t border-white/[0.08]">
                        <p className="text-xs text-white/40">
                          Les filtres s'appliquent à tous les exports. Laissez vide pour exporter toutes les données.
                        </p>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>
              
              {/* Active Filters Display */}
              {hasActiveFilters && (
                <div className="mb-4 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-white/50">Filtres actifs:</span>
                  {exportFilters.dateFrom && (
                    <Badge variant="outline" className="text-xs border-[#D9B35A]/30 text-[#D9B35A]">
                      <Calendar className="w-3 h-3 mr-1" />
                      Depuis: {exportFilters.dateFrom}
                    </Badge>
                  )}
                  {exportFilters.dateTo && (
                    <Badge variant="outline" className="text-xs border-[#D9B35A]/30 text-[#D9B35A]">
                      <Calendar className="w-3 h-3 mr-1" />
                      Jusqu'à: {exportFilters.dateTo}
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
                              <p className="text-xs text-white/40">{exp.count} entrées</p>
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
                              Télécharger CSV
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
                  <p>Chargement des options d'export...</p>
                </div>
              )}

              <div className="mt-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                <p className="text-sm text-blue-400">
                  <strong>Note:</strong> Les fichiers CSV sont encodés en UTF-8 avec BOM et utilisent le point-virgule (;) 
                  comme séparateur pour une compatibilité optimale avec Excel français.
                </p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Decision Dialog */}
      <Dialog open={decisionDialogOpen} onOpenChange={setDecisionDialogOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {decisionType === 'APPROVED' ? (
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-400" />
              )}
              {decisionType === 'APPROVED' ? 'Approuver la demande' : 'Rejeter la demande'}
            </DialogTitle>
            <DialogDescription className="text-white/60">
              {selectedApp?.org?.legal_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {decisionType === 'REJECTED' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Raison du rejet *</label>
                <Select value={rejectionReason} onValueChange={setRejectionReason}>
                  <SelectTrigger className="w-full bg-white/[0.04] border-white/10">
                    <SelectValue placeholder="Sélectionner une raison" />
                  </SelectTrigger>
                  <SelectContent>
                    {REJECTION_REASONS.map(reason => (
                      <SelectItem key={reason.code} value={reason.code}>
                        {reason.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Commentaire (optionnel)</label>
              <Textarea
                placeholder="Ajouter un commentaire..."
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                className="bg-white/[0.04] border-white/10"
                rows={3}
              />
            </div>

            {decisionType === 'APPROVED' && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-sm text-green-400">
                  L'approbation va créer automatiquement :
                </p>
                <ul className="text-xs text-green-400/80 mt-1 space-y-1">
                  <li>• Un wallet avec crédits initiaux</li>
                  <li>• L'accès à la zone du territoire</li>
                  <li>• Le compte partenaire KDMARCHE</li>
                </ul>
              </div>
            )}
          </div>

          <DialogFooter className="flex gap-3">
            <Button 
              variant="outline" 
              onClick={() => setDecisionDialogOpen(false)}
              className="border-white/10"
            >
              Annuler
            </Button>
            <Button
              onClick={handleDecision}
              disabled={submittingDecision || (decisionType === 'REJECTED' && !rejectionReason)}
              className={decisionType === 'APPROVED' 
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-red-500 hover:bg-red-600 text-white'
              }
            >
              {submittingDecision ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : decisionType === 'APPROVED' ? (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              ) : (
                <XCircle className="w-4 h-4 mr-2" />
              )}
              {decisionType === 'APPROVED' ? 'Confirmer l\'approbation' : 'Confirmer le rejet'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
