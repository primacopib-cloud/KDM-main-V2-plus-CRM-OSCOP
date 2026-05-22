import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, Package, Clock, CheckCircle2, XCircle, Truck,
  MapPin, Calendar, FileText, Loader2, ChevronDown, ChevronUp,
  AlertCircle, RefreshCw
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from '../components/ui/collapsible';

import { partners } from '../data/mock';
import { authAPI, ordersAPIV2 } from '../services/api';

// Order status configuration
const ORDER_STATUSES = {
  DRAFT: { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400', icon: FileText },
  PENDING: { label: 'En attente', color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  CONFIRMED: { label: 'Confirmée', color: 'bg-blue-500/20 text-blue-400', icon: CheckCircle2 },
  PROCESSING: { label: 'En préparation', color: 'bg-purple-500/20 text-purple-400', icon: Package },
  READY_FOR_PICKUP: { label: 'Prête à enlever', color: 'bg-[#57D19A]/20 text-[#57D19A]', icon: Truck },
  COMPLETED: { label: 'Terminée', color: 'bg-green-500/20 text-green-400', icon: CheckCircle2 },
  CANCELED: { label: 'Annulée', color: 'bg-red-500/20 text-red-400', icon: XCircle },
};

// Format price
const formatPrice = (cents) => {
  if (!cents) return '---';
  return (cents / 100).toFixed(2).replace('.', ',') + ' €';
};

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

export default function OrdersPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [expandedOrder, setExpandedOrder] = useState(null);
  
  // Cancel dialog
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [orderToCancel, setOrderToCancel] = useState(null);
  const [canceling, setCanceling] = useState(false);

  // Load orders
  useEffect(() => {
    const loadOrders = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion?redirect=/commandes');
        return;
      }

      try {
        const filter = statusFilter === 'all' ? null : statusFilter;
        const data = await ordersAPIV2.list(filter, 0, 50);
        setOrders(data);
      } catch (error) {
        console.error('Error loading orders:', error);
        toast.error('Erreur lors du chargement des commandes');
      } finally {
        setLoading(false);
      }
    };

    loadOrders();
  }, [navigate, statusFilter]);

  // Refresh orders
  const refreshOrders = async () => {
    setLoading(true);
    try {
      const filter = statusFilter === 'all' ? null : statusFilter;
      const data = await ordersAPIV2.list(filter, 0, 50);
      setOrders(data);
      toast.success('Commandes actualisées');
    } catch (error) {
      toast.error('Erreur lors de l\'actualisation');
    } finally {
      setLoading(false);
    }
  };

  // Cancel order
  const handleCancelOrder = async () => {
    if (!orderToCancel) return;

    setCanceling(true);
    try {
      await ordersAPIV2.cancel(orderToCancel.id, 'Annulation client');
      setOrders(prev => prev.map(o => 
        o.id === orderToCancel.id ? { ...o, status: 'CANCELED' } : o
      ));
      toast.success('Commande annulée');
      setCancelDialogOpen(false);
      setOrderToCancel(null);
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'annulation');
    } finally {
      setCanceling(false);
    }
  };

  // Stats
  const stats = {
    total: orders.length,
    pending: orders.filter(o => ['PENDING', 'CONFIRMED', 'PROCESSING'].includes(o.status)).length,
    ready: orders.filter(o => o.status === 'READY_FOR_PICKUP').length,
    completed: orders.filter(o => o.status === 'COMPLETED').length,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }} data-testid="orders-page">
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
              <span className="text-sm hidden sm:inline">Retour</span>
            </Link>
            <div className="flex items-center gap-3">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-12 w-auto object-contain" />
              <span className="text-white/40">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-8 w-auto object-contain" />
            </div>
          </div>
          
          <Button 
            variant="outline" 
            onClick={refreshOrders}
            className="border-white/10"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-6">
        {/* Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">Mes commandes</h1>
            <p className="text-white/60 text-sm">Historique et suivi de vos commandes</p>
          </div>
          
          <Link to="/catalogue">
            <Button className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
              <Package className="w-4 h-4 mr-2" />
              Nouvelle commande
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="glass-panel-soft rounded-[14px] p-4">
            <p className="text-xs text-white/50 mb-1">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <p className="text-xs text-white/50 mb-1">En cours</p>
            <p className="text-2xl font-bold text-yellow-400">{stats.pending}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <p className="text-xs text-white/50 mb-1">À enlever</p>
            <p className="text-2xl font-bold text-[#57D19A]">{stats.ready}</p>
          </div>
          <div className="glass-panel-soft rounded-[14px] p-4">
            <p className="text-xs text-white/50 mb-1">Terminées</p>
            <p className="text-2xl font-bold text-green-400">{stats.completed}</p>
          </div>
        </div>

        {/* Filter */}
        <div className="flex gap-3 mb-6">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[200px] bg-white/[0.04] border-white/10 text-white">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              <SelectItem value="PENDING">En attente</SelectItem>
              <SelectItem value="CONFIRMED">Confirmée</SelectItem>
              <SelectItem value="PROCESSING">En préparation</SelectItem>
              <SelectItem value="READY_FOR_PICKUP">Prête à enlever</SelectItem>
              <SelectItem value="COMPLETED">Terminée</SelectItem>
              <SelectItem value="CANCELED">Annulée</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Orders List */}
        <div className="space-y-4">
          {orders.length === 0 ? (
            <div className="text-center py-20 text-white/50">
              <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Aucune commande</p>
              <p className="text-sm mb-4">Commencez par parcourir le catalogue</p>
              <Link to="/catalogue">
                <Button className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
                  Voir le catalogue
                </Button>
              </Link>
            </div>
          ) : (
            orders.map(order => {
              const statusConfig = ORDER_STATUSES[order.status] || ORDER_STATUSES.PENDING;
              const StatusIcon = statusConfig.icon;
              const isExpanded = expandedOrder === order.id;
              const canCancel = ['PENDING', 'CONFIRMED'].includes(order.status);

              return (
                <Collapsible 
                  key={order.id} 
                  open={isExpanded}
                  onOpenChange={() => setExpandedOrder(isExpanded ? null : order.id)}
                >
                  <div className="glass-panel-soft rounded-[18px] overflow-hidden">
                    <CollapsibleTrigger className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${statusConfig.color.split(' ')[0]}`}>
                          <StatusIcon className={`w-5 h-5 ${statusConfig.color.split(' ')[1]}`} />
                        </div>
                        <div className="text-left">
                          <p className="font-semibold text-white/90">{order.order_number}</p>
                          <p className="text-xs text-white/50">{formatDate(order.created_at)}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <Badge className={statusConfig.color}>
                          {statusConfig.label}
                        </Badge>
                        <p className="font-bold text-[#D9B35A] hidden sm:block">
                          {formatPrice(order.total_ht_cents)} HT
                        </p>
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-white/40" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-white/40" />
                        )}
                      </div>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <div className="px-4 pb-4 border-t border-white/[0.06] pt-4">
                        {/* Order details */}
                        <div className="grid md:grid-cols-2 gap-6">
                          {/* Items */}
                          <div>
                            <h4 className="text-sm font-semibold text-white/70 mb-3">Articles</h4>
                            <div className="space-y-2">
                              {order.items?.map((item, idx) => (
                                <div key={idx} className="flex justify-between items-center p-2 rounded-lg bg-white/[0.02]">
                                  <div>
                                    <p className="text-sm text-white/90">{item.product_name}</p>
                                    <p className="text-xs text-white/50">{item.quantity} × {formatPrice(item.unit_price_ht_cents)}</p>
                                  </div>
                                  <p className="font-medium">{formatPrice(item.line_total_ht_cents)}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Pickup info */}
                          <div>
                            <h4 className="text-sm font-semibold text-white/70 mb-3">Point d'enlèvement (EXW)</h4>
                            {order.pickup_location ? (
                              <div className="p-3 rounded-xl bg-[#57D19A]/10 border border-[#57D19A]/20">
                                <div className="flex items-start gap-2">
                                  <MapPin className="w-4 h-4 text-[#57D19A] mt-0.5" />
                                  <div>
                                    <p className="font-medium text-white/90">{order.pickup_location.name}</p>
                                    <p className="text-xs text-white/60">{order.pickup_location.address}</p>
                                    <p className="text-xs text-white/60">{order.pickup_location.city}</p>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <p className="text-white/50 text-sm">Non défini</p>
                            )}

                            {/* Total */}
                            <div className="mt-4 p-3 rounded-xl bg-white/[0.04]">
                              <div className="flex justify-between items-center">
                                <span className="text-white/70">Total HT</span>
                                <span className="text-xl font-bold text-[#D9B35A]">{formatPrice(order.total_ht_cents)}</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        {canCancel && (
                          <div className="mt-4 pt-4 border-t border-white/[0.06] flex justify-end">
                            <Button
                              variant="outline"
                              onClick={() => {
                                setOrderToCancel(order);
                                setCancelDialogOpen(true);
                              }}
                              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                            >
                              <XCircle className="w-4 h-4 mr-2" />
                              Annuler la commande
                            </Button>
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
      </div>

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-400" />
              Annuler la commande
            </DialogTitle>
            <DialogDescription className="text-white/60">
              Êtes-vous sûr de vouloir annuler la commande {orderToCancel?.order_number} ?
              Cette action est irréversible.
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter className="flex gap-3">
            <Button 
              variant="outline" 
              onClick={() => setCancelDialogOpen(false)}
              className="border-white/10"
            >
              Non, conserver
            </Button>
            <Button 
              onClick={handleCancelOrder}
              disabled={canceling}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              {canceling ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <XCircle className="w-4 h-4 mr-2" />
              )}
              Oui, annuler
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
