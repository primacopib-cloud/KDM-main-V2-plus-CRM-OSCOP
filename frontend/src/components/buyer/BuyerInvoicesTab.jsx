import i18n from '@/i18n';
import {
  FileText, Search, Filter, Eye, Download, Receipt, Euro, Clock, CheckCircle2,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { TabsContent } from '../ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { formatCurrency, formatDate } from './buyerUtils';

export const BuyerInvoicesTab = ({
  invoices, filteredInvoices, invoiceStats, searchTerm, setSearchTerm,
  invoiceStatusFilter, setInvoiceStatusFilter, viewInvoiceDetails, downloadInvoicePDF,
}) => (
          <TabsContent value="invoices" className="space-y-6">
            {/* Invoice Stats */}
            {invoiceStats && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Total factures</p>
                      <FileText className="w-4 h-4 text-[#D9B35A]" />
                    </div>
                    <p className="text-2xl font-bold text-white">{invoiceStats.total_invoices}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Payées</p>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{invoiceStats.total_paid}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">{i18n.t('buyer.en_attente')}</p>
                      <Clock className="w-4 h-4 text-amber-400" />
                    </div>
                    <p className="text-2xl font-bold text-amber-400">{invoiceStats.total_pending}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Montant total</p>
                      <Euro className="w-4 h-4 text-purple-400" />
                    </div>
                    <p className="text-2xl font-bold text-purple-400">{formatCurrency(invoiceStats.total_amount_cents)}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder="Rechercher par numéro de facture..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white/[0.04] border-white/10 text-white"
                  data-testid="invoice-search-input"
                />
              </div>
              <Select value={invoiceStatusFilter} onValueChange={setInvoiceStatusFilter}>
                <SelectTrigger className="w-[180px] bg-white/[0.04] border-white/10" data-testid="invoice-status-filter">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="PENDING">{i18n.t('buyer.en_attente')}</SelectItem>
                  <SelectItem value="PAID">Payée</SelectItem>
                  <SelectItem value="PARTIAL">Partiel</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Invoices List */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Receipt className="w-5 h-5 text-[#D9B35A]" />
                  Factures
                </CardTitle>
                <CardDescription className="text-white/60">
                  Historique de vos factures et documents comptables
                </CardDescription>
              </CardHeader>
              <CardContent>
                {filteredInvoices.length === 0 ? (
                  <div className="text-center py-12 text-white/50" data-testid="no-invoices">
                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Aucune facture disponible</p>
                    <p className="text-sm">Les factures sont générées après validation des commandes</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="invoices-list">
                    {filteredInvoices.map(invoice => {
                      const isPaid = invoice.payment_status === 'PAID';
                      const isPending = invoice.payment_status === 'PENDING';
                      
                      return (
                        <div 
                          key={invoice.id}
                          className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] transition-colors"
                          data-testid={`invoice-item-${invoice.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                                isPaid ? 'bg-emerald-500/20' : 'bg-amber-500/20'
                              }`}>
                                {isPaid ? (
                                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                ) : (
                                  <Clock className="w-5 h-5 text-amber-400" />
                                )}
                              </div>
                              <div>
                                <p className="font-semibold text-white">{invoice.invoice_number}</p>
                                <p className="text-xs text-white/50">
                                  Commande {invoice.order_number} · {formatDate(invoice.issue_date)}
                                </p>
                              </div>
                            </div>
                            <Badge 
                              variant="outline" 
                              className={isPaid 
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                                : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                              }
                            >
                              {isPaid ? i18n.t('buyer.payee') : i18n.t('buyer.en_attente')}
                            </Badge>
                          </div>
                          
                          {/* Invoice Details */}
                          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                            <div>
                              <p className="text-white/50">Montant HT</p>
                              <p className="text-white/90">{formatCurrency(invoice.subtotal_ht_cents)}</p>
                            </div>
                            <div>
                              <p className="text-white/50">TVA ({(invoice.tax_rate * 100).toFixed(1)}%)</p>
                              <p className="text-white/90">{formatCurrency(invoice.tax_cents)}</p>
                            </div>
                            {invoice.total_fees_cents > 0 && (
                              <div>
                                <p className="text-white/50">Frais</p>
                                <p className="text-white/90">{formatCurrency(invoice.total_fees_cents)}</p>
                              </div>
                            )}
                            <div>
                              <p className="text-white/50">Total TTC</p>
                              <p className="font-bold text-[#D9B35A]">{formatCurrency(invoice.total_ttc_cents)}</p>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="text-white/60 hover:text-white"
                              onClick={() => viewInvoiceDetails(invoice)}
                              data-testid={`view-invoice-${invoice.id}`}
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              Détails
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="border-white/10"
                              onClick={() => downloadInvoicePDF(invoice)}
                              data-testid={`download-invoice-${invoice.id}`}
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Télécharger PDF
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

);
