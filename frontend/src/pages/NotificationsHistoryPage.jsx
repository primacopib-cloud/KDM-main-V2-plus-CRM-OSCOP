import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell, Search, Filter, Calendar, CheckCheck, Trash2,
  ChevronLeft, ChevronRight, X, FileText, User, Building2,
  Wallet, AlertTriangle, ShoppingCart, Truck, Package,
  CreditCard, Plus, Minus, ClipboardCheck, CheckCircle, XCircle,
  ArrowLeft, RefreshCw
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Icon mapping for notification types
const getNotificationIcon = (type) => {
  const icons = {
    new_quote: FileText,
    new_user: User,
    org_submitted: Building2,
    org_approved: CheckCircle,
    org_rejected: XCircle,
    subscription_activated: CreditCard,
    subscription_past_due: AlertTriangle,
    order_created: ShoppingCart,
    order_shipped: Truck,
    order_delivered: Package,
    wallet_credit: Plus,
    wallet_debit: Minus,
    system_alert: Bell,
    document_ready: FileText,
    pod_available: ClipboardCheck,
  };
  return icons[type] || Bell;
};

const getNotificationColor = (type) => {
  const colors = {
    new_quote: '#D9B35A',
    new_user: '#57D19A',
    org_submitted: '#3B82F6',
    org_approved: '#10B981',
    org_rejected: '#EF4444',
    subscription_activated: '#8B5CF6',
    subscription_past_due: '#F59E0B',
    order_created: '#06B6D4',
    order_shipped: '#14B8A6',
    order_delivered: '#22C55E',
    wallet_credit: '#10B981',
    wallet_debit: '#EF4444',
    system_alert: '#6B7280',
    document_ready: '#8B5CF6',
    pod_available: '#0EA5E9',
  };
  return colors[type] || '#6B7280';
};

const dateFilterOptions = [
  { value: 'all', label: 'Toutes les dates' },
  { value: 'today', label: "Aujourd'hui" },
  { value: 'yesterday', label: 'Hier' },
  { value: 'last_7_days', label: '7 derniers jours' },
  { value: 'last_30_days', label: '30 derniers jours' },
];

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return 'À l\'instant';
  if (diff < 3600000) return `Il y a ${Math.floor(diff / 60000)} min`;
  if (diff < 86400000) return `Il y a ${Math.floor(diff / 3600000)}h`;
  
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  });
};

export default function NotificationsHistoryPage() {
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Filters
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [readFilter, setReadFilter] = useState('all'); // all, read, unread

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchNotifications = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        include_stats: 'true',
        date_filter: dateFilter,
      });
      
      if (selectedType !== 'all') {
        params.append('notification_type', selectedType);
      }
      if (readFilter === 'read') {
        params.append('is_read', 'true');
      } else if (readFilter === 'unread') {
        params.append('is_read', 'false');
      }
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim());
      }
      
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/notifications/history?${params}`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setTotal(data.total || 0);
        setHasMore(data.has_more || false);
        if (data.stats) setStats(data.stats);
      }
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, pageSize, selectedType, dateFilter, readFilter, searchQuery]);

  const fetchTypes = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/notifications/types`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });
      if (res.ok) {
        const data = await res.json();
        setTypes(data.types || []);
      }
    } catch (error) {
      console.error('Error fetching types:', error);
    }
  }, []);

  useEffect(() => {
    fetchTypes();
  }, [fetchTypes]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAsRead = async (notificationId) => {
    try {
      const res = await fetch(`${API_URL}/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        setNotifications(prev => 
          prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
        );
        if (stats) {
          setStats({ ...stats, unread: Math.max(0, stats.unread - 1) });
        }
      }
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      const res = await fetch(`${API_URL}/api/notifications/read-all`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        if (stats) {
          setStats({ ...stats, unread: 0 });
        }
      }
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  const handleClearRead = async () => {
    if (!window.confirm('Supprimer toutes les notifications lues de plus de 30 jours ?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/notifications/history/clear-read`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        fetchNotifications(true);
      }
    } catch (error) {
      console.error('Error clearing read notifications:', error);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchNotifications();
  };

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedType('all');
    setDateFilter('all');
    setReadFilter('all');
    setPage(1);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-[#070A10] text-white">
      <NavBar />
      
      <main className="pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link 
              to="/espace-acheteur"
              className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-2xl font-bold">Historique des notifications</h1>
              <p className="text-white/60">Consultez et gérez toutes vos notifications</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fetchNotifications(true)}
              disabled={refreshing}
              className="text-white/60"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Actualiser
            </Button>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                    <Bell className="w-5 h-5 text-[#D9B35A]" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.total}</p>
                    <p className="text-xs text-white/50">Total</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
                    <Bell className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.unread}</p>
                    <p className="text-xs text-white/50">Non lues</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#57D19A]/20 flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-[#57D19A]" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.today || 0}</p>
                    <p className="text-xs text-white/50">Aujourd'hui</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stats.this_week || 0}</p>
                    <p className="text-xs text-white/50">Cette semaine</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div 
            className="p-4 rounded-2xl mb-6"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Rechercher dans les notifications..."
                    className="pl-10 bg-white/[0.04] border-white/10"
                    data-testid="notifications-search"
                  />
                </div>
              </form>

              {/* Type Filter */}
              <Select value={selectedType} onValueChange={(v) => { setSelectedType(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Filter className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les types</SelectItem>
                  {types.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Date Filter */}
              <Select value={dateFilter} onValueChange={(v) => { setDateFilter(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Calendar className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Période" />
                </SelectTrigger>
                <SelectContent>
                  {dateFilterOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Read Filter */}
              <Select value={readFilter} onValueChange={(v) => { setReadFilter(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-40 bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes</SelectItem>
                  <SelectItem value="unread">Non lues</SelectItem>
                  <SelectItem value="read">Lues</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Active filters & actions */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10">
              <div className="flex items-center gap-2">
                {(selectedType !== 'all' || dateFilter !== 'all' || readFilter !== 'all' || searchQuery) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="text-white/60"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Réinitialiser
                  </Button>
                )}
                <span className="text-sm text-white/50">
                  {total} notification{total !== 1 ? 's' : ''}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                {stats?.unread > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleMarkAllAsRead}
                    className="text-white/60"
                  >
                    <CheckCheck className="w-4 h-4 mr-2" />
                    Tout marquer comme lu
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearRead}
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Nettoyer
                </Button>
              </div>
            </div>
          </div>

          {/* Notifications List */}
          <div 
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            {loading ? (
              <div className="p-12 text-center">
                <div className="w-8 h-8 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-white/50">Chargement...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-12 text-center">
                <Bell className="w-12 h-12 text-white/20 mx-auto mb-4" />
                <p className="text-white/50">Aucune notification trouvée</p>
                {(selectedType !== 'all' || dateFilter !== 'all' || readFilter !== 'all' || searchQuery) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="mt-4"
                  >
                    Réinitialiser les filtres
                  </Button>
                )}
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {notifications.map((notification) => {
                  const Icon = getNotificationIcon(notification.type);
                  const color = getNotificationColor(notification.type);
                  
                  return (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-white/[0.02] transition-colors ${
                        !notification.is_read ? 'bg-white/[0.02]' : ''
                      }`}
                      data-testid={`notification-${notification.id}`}
                    >
                      <div className="flex gap-4">
                        {/* Icon */}
                        <div 
                          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${color}20` }}
                        >
                          <Icon className="w-5 h-5" style={{ color }} />
                        </div>
                        
                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className={`font-medium ${!notification.is_read ? 'text-white' : 'text-white/70'}`}>
                                  {notification.title}
                                </h4>
                                {!notification.is_read && (
                                  <span className="w-2 h-2 rounded-full bg-[#D9B35A]" />
                                )}
                              </div>
                              {notification.message && (
                                <p className="text-sm text-white/50 mt-1 line-clamp-2">
                                  {notification.message}
                                </p>
                              )}
                            </div>
                            <span className="text-xs text-white/40 whitespace-nowrap">
                              {formatDate(notification.created_at)}
                            </span>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center gap-2 mt-2">
                            {notification.action_url && (
                              <Link
                                to={notification.action_url}
                                className="text-xs text-[#D9B35A] hover:underline"
                              >
                                Voir détails →
                              </Link>
                            )}
                            {!notification.is_read && (
                              <button
                                onClick={() => handleMarkAsRead(notification.id)}
                                className="text-xs text-white/50 hover:text-white/70 ml-auto"
                              >
                                Marquer comme lu
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-white/50">
                Page {page} sur {totalPages}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="text-white/60"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Précédent
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage(p => p + 1)}
                  disabled={!hasMore}
                  className="text-white/60"
                >
                  Suivant
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
      
      <Footer />
    </div>
  );
}
