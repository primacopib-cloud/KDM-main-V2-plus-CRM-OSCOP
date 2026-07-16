import i18n from '@/i18n';
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '../components/ui/input';
import { partners } from '../data/mock';
import { 
  ArrowLeft, 
  Users, 
  FileText, 
  TrendingUp, 
  Wallet,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  CheckCircle,
  Clock,
  XCircle,
  Plus,
  Minus,
  Shield,
  Building2,
  MapPin
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI, adminAPI, organizationsAPI } from '../services/api';
import NotificationsDropdown from '../components/NotificationsDropdown';

const AdminPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState({ users: [], total: 0, page: 1, per_page: 20 });
  const [quotes, setQuotes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      if (!authAPI.isAuthenticated()) {
        navigate('/connexion');
        return;
      }
      
      try {
        const userData = await authAPI.getMe();
        setCurrentUser(userData);
        
        if (!userData.is_admin) {
          toast.error(i18n.t('adm.acces_reserve_aux_administrateurs'));
          navigate('/dashboard');
          return;
        }
        
        const [statsData, usersData, quotesData] = await Promise.all([
          adminAPI.getStats(),
          adminAPI.getUsers(1, 20),
          adminAPI.getQuotes()
        ]);
        
        setStats(statsData);
        setUsers(usersData);
        setQuotes(quotesData);
      } catch (error) {
        console.error('Failed to load admin data:', error);
        if (error.message?.includes('403') || error.message?.includes('admin')) {
          toast.error(i18n.t('adm.acces_non_autorise'));
          navigate('/dashboard');
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    loadData();
  }, [navigate]);

  const handleSearchUsers = async () => {
    try {
      const data = await adminAPI.getUsers(1, 20, searchTerm);
      setUsers(data);
    } catch (error) {
      toast.error(i18n.t('adm.erreur_lors_de_la_recherche'));
    }
  };

  const handlePageChange = async (newPage) => {
    try {
      const data = await adminAPI.getUsers(newPage, 20, searchTerm);
      setUsers(data);
    } catch (error) {
      toast.error(i18n.t('adm.erreur_lors_du_chargement'));
    }
  };

  const handleUpdateQuoteStatus = async (quoteId, newStatus) => {
    try {
      await adminAPI.updateQuoteStatus(quoteId, newStatus);
      setQuotes(prev => prev.map(q => q.id === quoteId ? { ...q, status: newStatus } : q));
      toast.success(i18n.t('adm.statut_mis_a_jour'));
    } catch (error) {
      toast.error(i18n.t('adm.erreur_lors_de_la_mise'));
    }
  };

  const handleUpdateCredits = async (userId, amount) => {
    try {
      await adminAPI.updateUserCredits(userId, amount);
      setUsers(prev => ({
        ...prev,
        users: prev.users.map(u => u.id === userId ? { ...u, credits: u.credits + amount } : u)
      }));
      toast.success(amount > 0 ? i18n.t('adm.credits_ajoutes') : i18n.t('adm.credits_retires'));
    } catch (error) {
      toast.error(i18n.t('adm.erreur_lors_de_la_mise'));
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: i18n.t('adm.vue_d_ensemble'), icon: TrendingUp },
    { id: 'users', label: i18n.t('adm.utilisateurs'), icon: Users },
    { id: 'quotes', label: i18n.t('adm.demandes'), icon: FileText },
  ];

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.86)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1160px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">{i18n.t('adm.retour')}</span>
            </Link>
            <span className="badge-status text-xs bg-red-500/20 text-red-400 border-red-500/30">
              <Shield className="w-3 h-3" />
              Admin
            </span>
          </div>
          <div className="flex items-center gap-3">
            <NotificationsDropdown isAdmin={true} />
            <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-10 w-auto object-contain" />
            <img src={partners.oscop.logo} alt="O'SCOP" className="h-8 w-auto object-contain" />
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">{i18n.t('adm.administration')}</h1>
          <p className="text-white/60 text-sm">{i18n.t('adm.gerez_les_utilisateurs_et_les')}</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                activeTab === tab.id 
                  ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30' 
                  : 'bg-white/[0.04] text-white/60 hover:text-white/90 border border-white/[0.08]'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="glass-panel-soft rounded-[18px] p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2.5 rounded-xl bg-[#D9B35A]/20">
                    <Users className="w-5 h-5 text-[#D9B35A]" />
                  </div>
                </div>
                <p className="text-xs text-white/60 mb-1">{i18n.t('adm.utilisateurs')}</p>
                <p className="text-2xl font-bold">{stats.total_users}</p>
                <p className="text-xs text-[#D4AF37] mt-1">+{stats.new_users_this_month} ce mois</p>
              </div>

              <div className="glass-panel-soft rounded-[18px] p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2.5 rounded-xl bg-[#D4AF37]/20">
                    <FileText className="w-5 h-5 text-[#D4AF37]" />
                  </div>
                </div>
                <p className="text-xs text-white/60 mb-1">{i18n.t('adm.demandes_de_devis')}</p>
                <p className="text-2xl font-bold">{stats.total_quotes}</p>
                <p className="text-xs text-[#D4AF37] mt-1">+{stats.new_quotes_this_month} ce mois</p>
              </div>

              <div className="glass-panel-soft rounded-[18px] p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2.5 rounded-xl bg-blue-500/20">
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                  </div>
                </div>
                <p className="text-xs text-white/60 mb-1">{i18n.t('adm.commandes')}</p>
                <p className="text-2xl font-bold">{stats.total_orders}</p>
              </div>

              <div className="glass-panel-soft rounded-[18px] p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2.5 rounded-xl bg-purple-500/20">
                    <Wallet className="w-5 h-5 text-purple-400" />
                  </div>
                </div>
                <p className="text-xs text-white/60 mb-1">{i18n.t('adm.credits_distribues')}</p>
                <p className="text-2xl font-bold">{stats.total_credits_distributed}</p>
              </div>
            </div>

            {/* Quotes by Status */}
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold mb-4">{i18n.t('adm.demandes_par_statut')}</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm text-yellow-400 font-medium">{i18n.t('adm.en_attente')}</span>
                  </div>
                  <p className="text-2xl font-bold">{stats.quotes_by_status?.pending || 0}</p>
                </div>
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-blue-400 font-medium">{i18n.t('adm.contacte')}</span>
                  </div>
                  <p className="text-2xl font-bold">{stats.quotes_by_status?.contacted || 0}</p>
                </div>
                <div className="p-4 rounded-xl bg-[#D4AF37]/10 border border-[#D4AF37]/20">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-4 h-4 text-[#D4AF37]" />
                    <span className="text-sm text-[#D4AF37] font-medium">{i18n.t('adm.converti')}</span>
                  </div>
                  <p className="text-2xl font-bold">{stats.quotes_by_status?.converted || 0}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-4">
            {/* Search */}
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder={i18n.t('adm.rechercher_par_email_entreprise')}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchUsers()}
                  className="pl-10 h-11 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40 rounded-xl"
                />
              </div>
              <button onClick={handleSearchUsers} className="btn-gold px-6 rounded-xl text-sm font-semibold">
                Rechercher
              </button>
            </div>

            {/* Users Table */}
            <div className="glass-panel-soft rounded-[18px] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/[0.08]">
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.entreprise')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.contact')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.email')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.abonnement')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.credits')}</th>
                      <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.users.map((user) => (
                      <tr key={user.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                        <td className="p-4">
                          <p className="font-medium text-white/90">{user.company_name}</p>
                          <p className="text-xs text-white/50">SIRET: {user.siret}</p>
                        </td>
                        <td className="p-4 text-white/80">{user.contact_name}</td>
                        <td className="p-4 text-white/80">{user.email}</td>
                        <td className="p-4">
                          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#D9B35A]/20 text-[#D9B35A]">
                            {user.subscription}
                          </span>
                        </td>
                        <td className="p-4 font-medium">{user.credits}</td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <button 
                              onClick={() => handleUpdateCredits(user.id, 100)}
                              className="p-1.5 rounded-lg bg-[#D4AF37]/20 text-[#D4AF37] hover:bg-[#D4AF37]/30"
                              title={i18n.t('adm.ajouter_100_credits')}
                            >
                              <Plus className="w-4 h-4" />
                            </button>
                            <button 
                              onClick={() => handleUpdateCredits(user.id, -50)}
                              className="p-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30"
                              title={i18n.t('adm.retirer_50_credits')}
                            >
                              <Minus className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {users.total > users.per_page && (
                <div className="flex items-center justify-between p-4 border-t border-white/[0.08]">
                  <p className="text-sm text-white/60">
                    {((users.page - 1) * users.per_page) + 1} - {Math.min(users.page * users.per_page, users.total)} sur {users.total}
                  </p>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handlePageChange(users.page - 1)}
                      disabled={users.page === 1}
                      className="p-2 rounded-lg bg-white/[0.04] disabled:opacity-50"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => handlePageChange(users.page + 1)}
                      disabled={users.page * users.per_page >= users.total}
                      className="p-2 rounded-lg bg-white/[0.04] disabled:opacity-50"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quotes Tab */}
        {activeTab === 'quotes' && (
          <div className="glass-panel-soft rounded-[18px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.08]">
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.date')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.entreprise')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.contact')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.email')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.formule')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.statut')}</th>
                    <th className="text-left p-4 text-xs uppercase tracking-wider text-white/60 font-semibold">{i18n.t('adm.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {quotes.map((quote) => (
                    <tr key={quote.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="p-4 text-white/60 text-sm">
                        {new Date(quote.created_at).toLocaleDateString(i18n.language)}
                      </td>
                      <td className="p-4 font-medium text-white/90">{quote.company}</td>
                      <td className="p-4 text-white/80">{quote.contact_name}</td>
                      <td className="p-4 text-white/80">{quote.email}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-white/[0.08] text-white/70">
                          {quote.plan || i18n.t('adm.non_specifie')}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          quote.status === 'converted' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                          quote.status === 'contacted' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {quote.status === 'converted' ? 'Converti' :
                           quote.status === 'contacted' ? i18n.t('adm.contacte') : i18n.t('adm.en_attente')}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-1">
                          {quote.status === 'pending' && (
                            <button 
                              onClick={() => handleUpdateQuoteStatus(quote.id, 'contacted')}
                              className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30"
                              title={i18n.t('adm.marquer_comme_contacte')}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                          )}
                          {quote.status === 'contacted' && (
                            <button 
                              onClick={() => handleUpdateQuoteStatus(quote.id, 'converted')}
                              className="p-1.5 rounded-lg bg-[#D4AF37]/20 text-[#D4AF37] hover:bg-[#D4AF37]/30"
                              title={i18n.t('adm.marquer_comme_converti')}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;
