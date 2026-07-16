import i18n from '@/i18n';
import {
  Package, ShoppingBag, MapPin, FileText, Receipt, Download,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../ui/dialog';
import { formatCurrency, formatDate, ORDER_STATUS } from './buyerUtils';

export const BuyerModals = ({
  orderModalOpen, setOrderModalOpen, selectedOrder,
  invoiceModalOpen, setInvoiceModalOpen, selectedInvoice, downloadInvoicePDF,
}) => (
  <>
      <Dialog open={orderModalOpen} onOpenChange={setOrderModalOpen}>
        <DialogContent className="bg-[#0c0f15] border-white/10 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-[#D9B35A]" />
              Détails de la commande
            </DialogTitle>
          </DialogHeader>
          
          {selectedOrder && (
            <div className="space-y-4">
              {/* Order Header */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold text-lg">{selectedOrder.order_number}</p>
                    <p className="text-sm text-white/50">{formatDate(selectedOrder.created_at)}</p>
                  </div>
                  <Badge variant="outline" className={ORDER_STATUS[selectedOrder.status]?.color || ''}>
                    {ORDER_STATUS[selectedOrder.status]?.label || selectedOrder.status}
                  </Badge>
                </div>
              </div>

              {/* Items */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <ShoppingBag className="w-4 h-4 text-[#D9B35A]" />
                  Articles ({selectedOrder.items?.length || 0})
                </h4>
                <div className="space-y-2">
                  {selectedOrder.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-white/[0.06] last:border-0">
                      <div>
                        <p className="text-sm font-medium text-white/90">{item.product_name}</p>
                        <p className="text-xs text-white/50">SKU: {item.product_sku}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm">{item.quantity} × {formatCurrency(item.price_ht_cents || item.unit_price_ht_cents)}</p>
                        <p className="text-xs text-white/50">{formatCurrency(item.line_total_ht_cents)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pickup Location */}
              {selectedOrder.pickup_location && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-emerald-400">
                    <MapPin className="w-4 h-4" />
                    Point de retrait EXW
                  </h4>
                  <p className="text-sm">{selectedOrder.pickup_location.name}</p>
                  <p className="text-xs text-white/60">{selectedOrder.pickup_location.address}, {selectedOrder.pickup_location.city}</p>
                </div>
              )}

              {/* Totals */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Sous-total HT</span>
                    <span>{formatCurrency(selectedOrder.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">TVA (8,5%)</span>
                    <span>{formatCurrency(selectedOrder.tax_cents)}</span>
                  </div>
                  {selectedOrder.is_installment && selectedOrder.installment_plan && (
                    <div className="flex justify-between text-sm text-purple-400">
                      <span>Frais paiement 4×</span>
                      <span>+{formatCurrency(selectedOrder.installment_plan.total_fees_cents)}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2 border-t border-white/[0.06]">
                    <span>Total TTC</span>
                    <span className="text-[#D9B35A]">{formatCurrency(selectedOrder.total_ttc_cents)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setOrderModalOpen(false)} className="border-white/10">
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={invoiceModalOpen} onOpenChange={setInvoiceModalOpen}>
        <DialogContent className="bg-[#0c0f15] border-white/10 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="w-5 h-5 text-[#D9B35A]" />
              Détails de la facture
            </DialogTitle>
          </DialogHeader>
          
          {selectedInvoice && (
            <div className="space-y-4">
              {/* Invoice Header */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold text-lg">{selectedInvoice.invoice_number}</p>
                    <p className="text-sm text-white/50">Commande: {selectedInvoice.order_number}</p>
                    <p className="text-xs text-white/40">Émise le {formatDate(selectedInvoice.issue_date)}</p>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={selectedInvoice.payment_status === 'PAID'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                      : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                    }
                  >
                    {selectedInvoice.payment_status === 'PAID' ? i18n.t('buyer.payee') : i18n.t('buyer.en_attente')}
                  </Badge>
                </div>
              </div>

              {/* Invoice Items */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#D9B35A]" />
                  Lignes de facturation ({selectedInvoice.items_count})
                </h4>
                <div className="space-y-2">
                  {selectedInvoice.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-white/[0.06] last:border-0">
                      <div>
                        <p className="text-sm font-medium text-white/90">{item.product_name}</p>
                        <p className="text-xs text-white/50">{item.quantity} {item.unit}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm">{formatCurrency(item.unit_price_ht_cents)} × {item.quantity}</p>
                        <p className="text-xs text-white/50">{formatCurrency(item.line_total_ht_cents)} HT</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Totals */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Sous-total HT</span>
                    <span>{formatCurrency(selectedInvoice.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">TVA ({(selectedInvoice.tax_rate * 100).toFixed(1)}%)</span>
                    <span>{formatCurrency(selectedInvoice.tax_cents)}</span>
                  </div>
                  {selectedInvoice.total_fees_cents > 0 && (
                    <>
                      <div className="flex justify-between text-sm text-purple-400">
                        <span>Frais HT</span>
                        <span>{formatCurrency(selectedInvoice.fees_ht_cents)}</span>
                      </div>
                      <div className="flex justify-between text-sm text-purple-400">
                        <span>TVA sur frais</span>
                        <span>{formatCurrency(selectedInvoice.fees_tax_cents)}</span>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2 border-t border-white/[0.06]">
                    <span>Total TTC</span>
                    <span className="text-[#D9B35A]">{formatCurrency(selectedInvoice.total_ttc_cents)}</span>
                  </div>
                  {selectedInvoice.payment_status === 'PENDING' && (
                    <div className="flex justify-between text-sm text-amber-400 pt-2">
                      <span>Reste à payer</span>
                      <span>{formatCurrency(selectedInvoice.balance_due_cents)}</span>
                    </div>
                  )}
                  {selectedInvoice.paid_at && (
                    <div className="flex justify-between text-sm text-emerald-400 pt-2">
                      <span>Payée le</span>
                      <span>{formatDate(selectedInvoice.paid_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Metadata */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-white/50">Zone</p>
                    <p className="text-white/90">{selectedInvoice.zone_code}</p>
                  </div>
                  <div>
                    <p className="text-white/50">Incoterm</p>
                    <p className="text-white/90">{selectedInvoice.incoterm}</p>
                  </div>
                  {selectedInvoice.payment_method && (
                    <div>
                      <p className="text-white/50">Mode de paiement</p>
                      <p className="text-white/90">{selectedInvoice.payment_method}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="gap-2">
            <Button 
              variant="outline" 
              onClick={() => downloadInvoicePDF(selectedInvoice)} 
              className="border-white/10"
            >
              <Download className="w-4 h-4 mr-2" />
              Télécharger PDF
            </Button>
            <Button variant="outline" onClick={() => setInvoiceModalOpen(false)} className="border-white/10">
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
  </>
);
