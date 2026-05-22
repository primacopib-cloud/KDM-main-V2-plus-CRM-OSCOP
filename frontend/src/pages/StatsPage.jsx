import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { partners } from '../data/mock';
import { 
  ArrowLeft, 
  TrendingUp, 
  Wallet, 
  ShoppingCart, 
  CreditCard,
  Calendar,
  Package,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  BarChart3,
  Clock
} from 'lucide-react';
import { authAPI, statsAPI } from '../services/api';

const StatsPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const loadStats = async () => {
      if (!authAPI.isAuthenticated()) {
        navigate('/connexion');
        return;
      }
      
      try {
        const data = await statsAPI.getUserStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadStats();
  }, [navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  const overview = stats?.overview || {};
  const recentOrders = stats?.recent_orders || [];
  const creditsHistory = stats?.credits_history || [];
  const monthlyStats = stats?.monthly_stats || [];

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(7,10,16,0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)'
        }}
      >
        <div className="max-w-[1160px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Retour</span>
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <img 
              src={partners.kdmarche.logo} 
              alt="KDMARCHE" 
              className="h-10 w-auto object-contain"
            />
            <img 
              src={partners.oscop.logo} 
              alt="O'SCOP" 
              className="h-8 w-auto object-contain"
            />
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-2">Mes Statistiques</h1>
          <p className="text-white/60 text-sm">Suivez vos commandes, crédits et économies</p>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(217,179,90,0.12)', border: '1px solid rgba(217,179,90,0.20)' }}>
                <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Total Commandes</p>
            <p className="text-2xl font-bold">{overview.total_orders || 0}</p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(87,209,154,0.12)', border: '1px solid rgba(87,209,154,0.20)' }}>
                <TrendingUp className="w-5 h-5 text-[#57D19A]" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Économies Totales</p>
            <p className="text-2xl font-bold text-[#57D19A]">{overview.total_savings?.toFixed(2) || '0.00'}€</p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(87,209,154,0.12)', border: '1px solid rgba(87,209,154,0.20)' }}>
                <Wallet className="w-5 h-5 text-[#57D19A]" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Crédits Disponibles</p>
            <p className="text-2xl font-bold">{overview.current_credits || 0}</p>
          </div>

          <div className="glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)' }}>
                <CreditCard className="w-5 h-5 text-white/70" />
              </div>
            </div>
            <p className="text-xs text-white/60 mb-1">Total Dépensé</p>
            <p className="text-2xl font-bold">{overview.total_spent?.toFixed(2) || '0.00'}€</p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Recent Orders */}
          <div className="md:col-span-2 glass-panel-soft rounded-[18px] p-5">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold flex items-center gap-2">
                <Package className="w-4 h-4" />
                Commandes Récentes
              </h3>
            </div>
            
            {recentOrders.length === 0 ? (
              <div className="text-center py-10">
                <Package className="w-12 h-12 text-white/20 mx-auto mb-3" />
                <p className="text-white/50">Aucune commande pour le moment</p>
                <p className="text-white/30 text-sm mt-1">Vos commandes apparaîtront ici</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentOrders.map((order, index) => (
                  <div 
                    key={index}
                    className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/[0.04]">
                        <ShoppingCart className="w-4 h-4 text-white/60" />
                      </div>
                      <div>
                        <p className="font-medium text-white/90">{order.items_count} article(s)</p>
                        <p className="text-xs text-white/50">
                          {new Date(order.date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{order.amount?.toFixed(2)}€</p>
                      {order.savings > 0 && (
                        <p className="text-xs text-[#57D19A]">-{order.savings?.toFixed(2)}€</p>
                      )}
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      order.status === 'delivered' ? 'bg-[#57D19A]/20 text-[#57D19A]' :
                      order.status === 'shipped' ? 'bg-blue-500/20 text-blue-400' :
                      order.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-white/10 text-white/60'
                    }`}>
                      {order.status === 'delivered' ? 'Livré' :
                       order.status === 'shipped' ? 'Expédié' :
                       order.status === 'processing' ? 'En cours' :
                       order.status === 'cancelled' ? 'Annulé' : 'En attente'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Credits History */}
          <div className="glass-panel-soft rounded-[18px] p-5">
            <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold flex items-center gap-2 mb-5">
              <Wallet className="w-4 h-4" />
              Historique Crédits
            </h3>
            
            {creditsHistory.length === 0 ? (
              <div className="text-center py-8">
                <Clock className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <p className="text-white/50 text-sm">Pas d'historique</p>
              </div>
            ) : (
              <div className="space-y-3">
                {creditsHistory.slice(0, 8).map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02]">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        item.type === 'added' ? 'bg-[#57D19A]/20' : 'bg-red-500/20'
                      }`}>
                        {item.type === 'added' ? (
                          <ArrowUpRight className="w-4 h-4 text-[#57D19A]" />
                        ) : (
                          <ArrowDownRight className="w-4 h-4 text-red-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm text-white/80">{item.description || (item.type === 'added' ? 'Ajout' : 'Utilisation')}</p>
                        <p className="text-xs text-white/40">
                          {new Date(item.date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    </div>
                    <span className={`font-semibold ${item.type === 'added' ? 'text-[#57D19A]' : 'text-red-400'}`}>
                      {item.type === 'added' ? '+' : '-'}{item.amount}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Monthly Stats Chart */}
        {monthlyStats.length > 0 && (
          <div className="mt-6 glass-panel-soft rounded-[18px] p-5">
            <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold flex items-center gap-2 mb-5">
              <BarChart3 className="w-4 h-4" />
              Évolution Mensuelle
            </h3>
            <div className="grid grid-cols-6 gap-4">
              {monthlyStats.slice(0, 6).reverse().map((month, index) => (
                <div key={index} className="text-center">
                  <div className="h-24 flex items-end justify-center mb-2">
                    <div 
                      className="w-8 rounded-t-lg bg-gradient-to-t from-[#D9B35A] to-[#F2D07A]"
                      style={{ height: `${Math.max(10, (month.spent / (Math.max(...monthlyStats.map(m => m.spent)) || 1)) * 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-white/50 truncate">{month.month?.split(' ')[0]}</p>
                  <p className="text-sm font-semibold">{month.spent?.toFixed(0) || 0}€</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsPage;
