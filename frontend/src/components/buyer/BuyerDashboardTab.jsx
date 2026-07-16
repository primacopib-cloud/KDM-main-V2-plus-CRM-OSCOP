import { Link } from 'react-router-dom';
import {
  Package, Clock, TrendingUp, Wallet, ChevronRight, FileText,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { TabsContent } from '../ui/tabs';
import { formatCurrency, formatShortDate, ORDER_STATUS } from './buyerUtils';

export const BuyerDashboardTab = ({ stats, orders, setActiveTab }) => (
          <TabsContent value="dashboard" className="space-y-6">
            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Commandes totales</p>
                    <Package className="w-4 h-4 text-[#D9B35A]" />
                  </div>
                  <p className="text-2xl font-bold text-white">{stats.totalOrders}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">En cours</p>
                    <Clock className="w-4 h-4 text-amber-400" />
                  </div>
                  <p className="text-2xl font-bold text-amber-400">{stats.pendingOrders}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Total dépensé</p>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <p className="text-2xl font-bold text-emerald-400">{formatCurrency(stats.totalSpent)}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Crédits O'SCOP</p>
                    <Wallet className="w-4 h-4 text-purple-400" />
                  </div>
                  <p className="text-2xl font-bold text-purple-400">{formatCurrency(stats.creditsBalance)}</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Orders */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Package className="w-5 h-5 text-[#D9B35A]" />
                    Commandes récentes
                  </CardTitle>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setActiveTab('orders')}
                    className="text-white/60 hover:text-white"
                  >
                    Voir tout <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {orders.length === 0 ? (
                  <div className="text-center py-8 text-white/50">
                    <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune commande</p>
                    <Link to="/catalogue">
                      <Button className="mt-4 bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
                        Commander
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {orders.slice(0, 5).map(order => {
                      const status = ORDER_STATUS[order.status] || ORDER_STATUS.PENDING;
                      const StatusIcon = status.icon;
                      return (
                        <div 
                          key={order.id}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between hover:bg-white/[0.04] transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${status.color.split(' ')[0]}`}>
                              <StatusIcon className={`w-4 h-4 ${status.color.split(' ')[1]}`} />
                            </div>
                            <div>
                              <p className="font-medium text-white/90 text-sm">{order.order_number}</p>
                              <p className="text-xs text-white/50">{formatShortDate(order.created_at)} · {order.items_count} article(s)</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant="outline" className={status.color}>{status.label}</Badge>
                            <p className="text-sm font-semibold text-[#D9B35A] mt-1">{formatCurrency(order.total_ttc_cents)} TTC</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <div className="grid sm:grid-cols-3 gap-4">
              <Link to="/catalogue">
                <Card className="bg-gradient-to-br from-[#D9B35A]/10 to-[#D9B35A]/5 border-[#D9B35A]/20 hover:border-[#D9B35A]/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                      <Package className="w-6 h-6 text-[#D9B35A]" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Nouvelle commande</p>
                      <p className="text-xs text-white/60">Accéder au catalogue</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/wallet">
                <Card className="bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-500/20 hover:border-purple-500/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                      <Wallet className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Recharger crédits</p>
                      <p className="text-xs text-white/60">Gérer mon wallet</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/legal">
                <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                      <FileText className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Documents légaux</p>
                      <p className="text-xs text-white/60">CGV, Contrats</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </TabsContent>
);
