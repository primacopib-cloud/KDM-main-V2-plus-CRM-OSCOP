import i18n from '@/i18n';
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
import { ApplicationsTab } from '../components/adminv2/ApplicationsTab';
import { OrganizationsTab } from '../components/adminv2/OrganizationsTab';
import { ExportTab } from '../components/adminv2/ExportTab';
import { DecisionDialog } from '../components/adminv2/DecisionDialog';

// Application status configuration
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
        toast.error(i18n.t('adm.veuillez_vous_connecter'));
        navigate('/connexion');
        return;
      }

      try {
        const userData = await authAPI.getMe();
        if (!userData.is_admin) {
          toast.error(i18n.t('adm.acces_reserve_aux_administrateurs'));
          navigate('/dashboard');
          return;
        }

        // Load applications and orgs
        await loadData();

      } catch (error) {
        console.error('Init error:', error);
        toast.error(i18n.t('adm.erreur_de_chargement'));
      } finally {
        setLoading(false);
      }
    };

    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appStatusFilter, orgStatusFilter]);

  // Handle decision
  const handleDecision = async () => {
    if (!selectedApp || !decisionType) return;

    if (decisionType === 'REJECTED' && !rejectionReason) {
      toast.error(i18n.t('adm.veuillez_selectionner_une_raison_de'));
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

      toast.success(decisionType === 'APPROVED' ? i18n.t('adm.demande_approuvee') : i18n.t('adm.demande_rejetee'));
      
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
      toast.error(error.message || i18n.t('adm.erreur_decision'));
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
      toast.success(i18n.t('adm.export_telecharge', { type: exportType }));
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
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }} data-testid="admin-v2-page">
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(30,12,52,0.88)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">{i18n.t('adm.retour')}</span>
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
          <h1 className="text-2xl font-bold mb-1">{i18n.t('adm.administration_b2b')}</h1>
          <p className="text-white/60 text-sm">{i18n.t('adm.gestion_des_demandes_d_adhesion')}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-white/50" />
              <p className="text-xs text-white/50">{i18n.t('adm.total_demandes')}</p>
            </div>
            <p className="text-2xl font-bold">{appStats.total}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-yellow-400" />
              <p className="text-xs text-white/50">{i18n.t('adm.en_attente')}</p>
            </div>
            <p className="text-2xl font-bold text-yellow-400">{appStats.pending}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <p className="text-xs text-white/50">{i18n.t('adm.approuvees')}</p>
            </div>
            <p className="text-2xl font-bold text-green-400">{appStats.approved}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <p className="text-xs text-white/50">{i18n.t('adm.rejetees')}</p>
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
              {i18n.t('adm.demandes_adhesion')}
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
          <ApplicationsTab
            applications={applications}
            appStatusFilter={appStatusFilter}
            setAppStatusFilter={setAppStatusFilter}
            expandedApp={expandedApp}
            setExpandedApp={setExpandedApp}
            openDecisionDialog={openDecisionDialog}
          />

          <OrganizationsTab
            organizations={organizations}
            orgStatusFilter={orgStatusFilter}
            setOrgStatusFilter={setOrgStatusFilter}
          />

          <ExportTab
            applications={applications}
            organizations={organizations}
            exportSummary={exportSummary}
            exportLoading={exportLoading}
            exportFilters={exportFilters}
            setExportFilters={setExportFilters}
            showFilters={showFilters}
            setShowFilters={setShowFilters}
            handleExportDownload={handleExportDownload}
            clearExportFilters={clearExportFilters}
          />
        </Tabs>
      </div>

      <DecisionDialog
        decisionDialogOpen={decisionDialogOpen}
        setDecisionDialogOpen={setDecisionDialogOpen}
        selectedApp={selectedApp}
        decisionType={decisionType}
        rejectionReason={rejectionReason}
        setRejectionReason={setRejectionReason}
        decisionComment={decisionComment}
        setDecisionComment={setDecisionComment}
        submittingDecision={submittingDecision}
        handleDecision={handleDecision}
      />
    </div>
  );
}
