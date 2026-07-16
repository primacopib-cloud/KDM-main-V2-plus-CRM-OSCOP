import i18n from '@/i18n';
import { Link } from 'react-router-dom';
import {
  Package, FileText, Search, Filter, Eye, Download, MapPin,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { formatCurrency, formatDate, ORDER_STATUS } from './buyerUtils';

export const BuyerOrdersTab = ({
  orders, filteredOrders, searchTerm, setSearchTerm,
  orderStatusFilter, setOrderStatusFilter, viewOrderDetails,
}) => (
          <TabsContent value="orders" className="space-y-6">
            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder="Rechercher par numéro..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white/[0.04] border-white/10 text-white"
                />
              </div>
              <Select value={orderStatusFilter} onValueChange={setOrderStatusFilter}>
                <SelectTrigger className="w-[180px] bg-white/[0.04] border-white/10">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="PENDING">{i18n.t('buyer.en_attente')}</SelectItem>
                  <SelectItem value="CONFIRMED">Confirmée</SelectItem>
                  <SelectItem value="PROCESSING">En préparation</SelectItem>
                  <SelectItem value="READY_FOR_PICKUP">Prête à enlever</SelectItem>
                  <SelectItem value="COMPLETED">Terminée</SelectItem>
                  <SelectItem value="CANCELED">Annulée</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Orders List */}
            {filteredOrders.length === 0 ? (
              <div className="text-center py-16 text-white/50">
                <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">Aucune commande trouvée</p>
                <p className="text-sm mb-4">Modifiez vos filtres ou passez une commande</p>
                <Link to="/catalogue">
                  <Button className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
                    Voir le catalogue
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredOrders.map(order => {
                  const status = ORDER_STATUS[order.status] || ORDER_STATUS.PENDING;
                  const StatusIcon = status.icon;
                  
                  return (
                    <Card key={order.id} className="bg-white/[0.04] border-white/[0.08] overflow-hidden">
                      <CardContent className="p-0">
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${status.color.split(' ')[0]}`}>
                                <StatusIcon className={`w-5 h-5 ${status.color.split(' ')[1]}`} />
                              </div>
                              <div>
                                <p className="font-semibold text-white">{order.order_number}</p>
                                <p className="text-xs text-white/50">
                                  {formatDate(order.created_at)}
                                  {order.is_installment && (
                                    <span className="ml-2 text-purple-400">· Paiement 4×</span>
                                  )}
                                </p>
                              </div>
                            </div>
                            <Badge variant="outline" className={status.color}>{status.label}</Badge>
                          </div>

                          {/* Order Items Preview */}
                          <div className="space-y-2 mb-4">
                            {order.items?.slice(0, 3).map((item, idx) => (
                              <div key={idx} className="flex justify-between items-center text-sm p-2 rounded-lg bg-white/[0.02]">
                                <span className="text-white/80">{item.product_name}</span>
                                <span className="text-white/50">{item.quantity} × {formatCurrency(item.unit_price_ht_cents)}</span>
                              </div>
                            ))}
                            {(order.items?.length || 0) > 3 && (
                              <p className="text-xs text-white/40 text-center">+ {order.items.length - 3} autres articles</p>
                            )}
                          </div>

                          {/* Pickup Location */}
                          {order.pickup_location && (
                            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 mb-4">
                              <div className="flex items-center gap-2 text-emerald-400">
                                <MapPin className="w-4 h-4" />
                                <span className="text-sm font-medium">Point de retrait EXW</span>
                              </div>
                              <p className="text-sm text-white/70 mt-1">{order.pickup_location.name} - {order.pickup_location.city}</p>
                            </div>
                          )}

                          {/* Totals */}
                          <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
                            <div className="text-sm">
                              <span className="text-white/50">Total HT : </span>
                              <span className="text-white/80">{formatCurrency(order.subtotal_ht_cents)}</span>
                            </div>
                            <div>
                              <span className="text-white/50 text-sm">Total TTC : </span>
                              <span className="text-xl font-bold text-[#D9B35A]">{formatCurrency(order.total_ttc_cents)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="px-4 py-3 bg-white/[0.02] border-t border-white/[0.06] flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" onClick={() => viewOrderDetails(order)} data-testid={`order-details-btn-${order.order_number}`}>
                              <Eye className="w-4 h-4 mr-2" />
                              Détails
                            </Button>
                            <Link to={`/bon-de-commande?order=${order.id}`}>
                              <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
                                <FileText className="w-4 h-4 mr-2" />
                                Bon de commande
                              </Button>
                            </Link>
                          </div>
                          {order.status === 'COMPLETED' && (
                            <Button variant="ghost" size="sm" className="text-emerald-400 hover:text-emerald-300">
                              <Download className="w-4 h-4 mr-2" />
                              Facture
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

);
