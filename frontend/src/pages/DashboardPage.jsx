import i18n from '@/i18n';
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Progress } from '../components/ui/progress';
import { partners, subscriptionPlans } from '../data/mock';
import { 
  LogOut, 
  User, 
  Wallet, 
  FileText, 
  Download, 
  Settings, 
  ShoppingCart,
  TrendingUp,
  MapPin,
  CreditCard,
  Plus,
  HelpCircle,
  Loader2,
  BarChart3,
  Shield
} from 'lucide-react';
import { toast } from 'sonner';
import { authAPI, creditsAPI, downloadOffer } from '../services/api';
import { BuyerCreditHistory } from '../components/BuyerCreditHistory';

const DashboardPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [addingCredits, setAddingCredits] = useState(false);

  useEffect(() => {
    const loadUser = async () => {
      if (!authAPI.isAuthenticated()) {
        navigate('/connexion');
        return;
      }
      
      try {
        const userData = await authAPI.getMe();
        setUser(userData);
      } catch (error) {
        console.error('Failed to load user:', error);
        authAPI.logout();
        navigate('/connexion');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUser();
  }, [navigate]);

  const handleLogout = () => {
    authAPI.logout();
    toast.success('Déconnexion réussie');
    navigate('/');
  };

  const handleAddCredits = async (amount) => {
    setAddingCredits(true);
    try {
      const result = await creditsAPI.add(amount);
      setUser(prev => ({ ...prev, credits: result.credits }));
      toast.success(result.message);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setAddingCredits(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  if (!user) return null;

  const currentPlan = subscriptionPlans.find(p => p.id === user.subscription);

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
            <Link to="/" className="flex items-center gap-3">
              <img 
                src={partners.kdmarche.logo} 
                alt="KDMARCHE" 
                className="h-36 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 2px 6px rgba(217,179,90,0.35))' }}
              />
              <img 
                src={partners.oscop.logo} 
                alt="O'SCOP" 
                className="h-20 w-auto object-contain"
                style={{ filter: 'drop-shadow(0 2px 6px rgba(212,175,55,0.35))' }}
              />
            </Link>
            <span className="badge-status text-xs">
              <span className="dot"></span>
              Espace Client
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white/90">{user.contact_name}</p>
              <p className="text-xs text-white/60">{user.company_name}</p>
            </div>
            <button 
              onClick={handleLogout} 
              className="btn-ghost p-2.5 rounded-xl"
              title="Déconnexion"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-8">
        {/* Welcome Banner */}
        <div 
          className="rounded-[22px] p-6 mb-6 relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(217,179,90,0.15), rgba(212,175,55,0.10))',
            border: '1px solid rgba(217,179,90,0.25)'
          }}
        >
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold mb-2">Bienvenue, {user.contact_name} !</h1>
              <p className="text-white/70 text-sm">Accédez à la centrale d&apos;achats B2B ESS</p>
            </div>
            <Link to="/catalogue">
              <button className="btn-gold inline-flex items-center justify-center gap-2 rounded-[14px] px-4 py-3 text-sm font-semibold">
                <ShoppingCart className="w-4 h-4" />
                Accéder au catalogue
              </button>
            </Link>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-3.5 mb-6">
          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(217,179,90,0.12)', border: '1px solid rgba(217,179,90,0.20)' }}>
                <CreditCard className="w-5 h-5 text-[#D9B35A]" />
              </div>
              <span className="ribbon text-[10px]">{currentPlan?.name || user.subscription}</span>
            </div>
            <p className="text-xs text-white/60 mb-1">Abonnement actif</p>
            <p className="text-xl font-bold">{currentPlan?.price || '---'}€ <span className="text-sm font-normal text-white/50">HT/mois</span></p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(212,175,55,0.12)', border: '1px solid rgba(212,175,55,0.20)' }}>
                <Wallet className="w-5 h-5 text-[#D4AF37]" />
              </div>
              <button 
                className="btn-ghost p-1.5 rounded-lg"
                onClick={() => handleAddCredits(100)}
                disabled={addingCredits}
              >
                {addingCredits ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-white/60 mb-1">Wallet Crédits</p>
            <p className="text-xl font-bold">{user.credits} <span className="text-sm font-normal text-white/50">crédits</span></p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(212,175,55,0.12)', border: '1px solid rgba(212,175,55,0.20)' }}>
                <TrendingUp className="w-5 h-5 text-[#D4AF37]" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Économies réalisées</p>
            <p className="text-xl font-bold">-- € <span className="text-sm font-normal text-[#D4AF37]">ce mois</span></p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(212,175,55,0.34)' }}>
                <MapPin className="w-5 h-5 text-white/70" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Zones actives</p>
            <p className="text-xl font-bold">1 <span className="text-sm font-normal text-white/50">zone</span></p>
          </div>
        </div>

        <BuyerCreditHistory />

        <div className="grid md:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-5">
            {/* Quick Actions */}
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold mb-4">Actions rapides</h3>
              <div className="grid sm:grid-cols-2 gap-3">
                <Link to="/catalogue" className="h-auto p-4 rounded-xl text-left flex items-center gap-3 transition-all hover:-translate-y-0.5" style={{ background: 'rgba(217,179,90,0.08)', border: '1px solid rgba(217,179,90,0.15)' }}>
                  <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Catalogue KDMARCHE</p>
                    <p className="text-xs text-white/60">Parcourir les produits</p>
                  </div>
                </Link>
                
                <Link to="/commandes" className="h-auto p-4 rounded-xl text-left flex items-center gap-3 transition-all hover:-translate-y-0.5" style={{ background: 'rgba(212,175,55,0.08)', border: '1px solid rgba(212,175,55,0.15)' }}>
                  <FileText className="w-5 h-5 text-[#D4AF37]" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Mes commandes</p>
                    <p className="text-xs text-white/60">Historique et suivi</p>
                  </div>
                </Link>
                
                <Link to="/espace-acheteur" className="h-auto p-4 rounded-xl text-left flex items-center gap-3 transition-all hover:-translate-y-0.5" style={{ background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.15)' }}>
                  <User className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Espace Acheteur Pro</p>
                    <p className="text-xs text-white/60">Dashboard complet</p>
                  </div>
                </Link>
                
                <button 
                  className="h-auto p-4 rounded-xl text-left flex items-center gap-3 glass-panel-soft transition-all hover:-translate-y-0.5"
                  onClick={downloadOffer}
                >
                  <Download className="w-5 h-5 text-white/70" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Offre commerciale</p>
                    <p className="text-xs text-white/60">Télécharger le PDF</p>
                  </div>
                </button>
                
                <button className="h-auto p-4 rounded-xl text-left flex items-center gap-3 glass-panel-soft transition-all hover:-translate-y-0.5">
                  <Settings className="w-5 h-5 text-white/70" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Paramètres</p>
                    <p className="text-xs text-white/60">Gérer mon compte</p>
                  </div>
                </button>
                
                <Link to="/statistiques" className="h-auto p-4 rounded-xl text-left flex items-center gap-3 transition-all hover:-translate-y-0.5" style={{ background: 'rgba(212,175,55,0.08)', border: '1px solid rgba(212,175,55,0.15)' }}>
                  <BarChart3 className="w-5 h-5 text-[#D4AF37]" />
                  <div>
                    <p className="font-medium text-white/90 text-sm">Statistiques</p>
                    <p className="text-xs text-white/60">Commandes et crédits</p>
                  </div>
                </Link>
                
                {user.is_admin && (
                  <Link to="/admin-v2" className="h-auto p-4 rounded-xl text-left flex items-center gap-3 transition-all hover:-translate-y-0.5" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
                    <Shield className="w-5 h-5 text-red-400" />
                    <div>
                      <p className="font-medium text-white/90 text-sm">Admin B2B</p>
                      <p className="text-xs text-white/60">Gérer les demandes</p>
                    </div>
                  </Link>
                )}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold mb-4">Activité récente</h3>
              <div className="space-y-3">
                {[
                  { action: 'Connexion au compte', time: 'À l\'instant', icon: User },
                  { action: 'Compte créé', time: new Date(user.created_at).toLocaleDateString(i18n.language), icon: User },
                ].map((item) => (
                  <div key={`activity-${item.action}`} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-white/[0.04] border border-white/[0.08]">
                      <item.icon className="w-4 h-4 text-white/60" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white/85">{item.action}</p>
                      <p className="text-xs text-white/50">{item.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-5">
            {/* Subscription Info */}
            <div className="glass-panel-soft rounded-[18px] p-5">
              <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold mb-4">Mon abonnement</h3>
              <div className="p-4 rounded-xl callout-gold mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-white/90">{currentPlan?.name || user.subscription}</span>
                  <span className="badge-status text-[10px]">
                    <span className="dot"></span>
                    Actif
                  </span>
                </div>
                <p className="text-2xl font-bold text-white">{currentPlan?.price || '---'}€ <span className="text-sm font-normal text-white/60">HT/mois</span></p>
              </div>
              
              <div className="mb-4">
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-white/60">Période en cours</span>
                  <span className="text-white/90 font-medium">En cours</span>
                </div>
                <Progress value={50} className="h-2 bg-white/10" />
              </div>
              
              <button className="btn-ghost w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium">
                Changer de formule
              </button>
            </div>

            {/* Support */}
            <div 
              className="rounded-[18px] p-5 relative overflow-hidden"
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
                border: '1px solid rgba(255,255,255,0.10)'
              }}
            >
              <div className="flex items-center gap-3 mb-3">
                <HelpCircle className="w-5 h-5 text-[#D4AF37]" />
                <h3 className="font-semibold">Besoin d&apos;aide ?</h3>
              </div>
              <p className="text-white/60 text-sm mb-4">Notre équipe est disponible pour vous accompagner.</p>
              <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold">
                Contacter le support
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
