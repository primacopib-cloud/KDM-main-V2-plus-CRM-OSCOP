import React, { useState } from 'react';
import {
  Package, CheckCircle2, XCircle, Clock, Eye, Search, Filter,
  RefreshCw, Building2, AlertTriangle, Flag, ChevronDown,
  ThumbsUp, ThumbsDown, MessageSquare
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '../ui/dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../ui/select';
import { toast } from 'sonner';

export const getStatusBadge = (status) => {
  switch (status) {
    case 'pending_approval':
      return <Badge className="bg-amber-100 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
    case 'approved':
      return <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Approuvé</Badge>;
    case 'rejected':
      return <Badge className="bg-red-100 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Rejeté</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
};

// ===== PRODUCT DETAIL MODAL =====
export const ProductDetailModal = ({ product, isOpen, onClose, onApprove, onReject }) => {
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleApprove = async () => {
    setLoading(true);
    await onApprove(product.id);
    setLoading(false);
    onClose();
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      toast.error('Veuillez indiquer un motif de rejet');
      return;
    }
    setLoading(true);
    await onReject(product.id, rejectionReason);
    setLoading(false);
    setShowRejectForm(false);
    onClose();
  };

  if (!product) return null;

  const formatCurrency = (amount) => 
    new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount || 0);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-5 h-5 text-purple-600" />
            Validation du produit
          </DialogTitle>
          <DialogDescription>
            Examinez les informations et décidez d'approuver ou de rejeter ce produit.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Status Banner */}
          <div className={`p-4 rounded-lg ${
            product.status === 'pending_approval' ? 'bg-amber-50 border border-amber-200' :
            product.status === 'approved' ? 'bg-emerald-50 border border-emerald-200' :
            'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {product.status === 'pending_approval' && <Clock className="w-5 h-5 text-amber-600" />}
                {product.status === 'approved' && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                {product.status === 'rejected' && <XCircle className="w-5 h-5 text-red-600" />}
                <span className="font-medium">
                  {product.status === 'pending_approval' && 'En attente de validation'}
                  {product.status === 'approved' && 'Produit approuvé'}
                  {product.status === 'rejected' && 'Produit rejeté'}
                </span>
              </div>
              {getStatusBadge(product.status)}
            </div>
            {product.rejection_reason && (
              <p className="mt-2 text-sm text-red-700">
                <strong>Motif:</strong> {product.rejection_reason}
              </p>
            )}
          </div>

          {/* Product Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label className="text-gray-500">Nom du produit</Label>
              <p className="font-semibold text-lg">{product.name}</p>
            </div>
            <div>
              <Label className="text-gray-500">SKU</Label>
              <p className="font-mono">{product.sku}</p>
            </div>
            <div>
              <Label className="text-gray-500">Catégorie</Label>
              <p className="capitalize">{product.category}</p>
            </div>
            <div className="col-span-2">
              <Label className="text-gray-500">Description</Label>
              <p className="text-gray-700">{product.description || '—'}</p>
            </div>
          </div>

          {/* Pricing */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold mb-3">Tarification</h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-gray-500">Prix HT</Label>
                <p className="font-bold text-lg">{formatCurrency(product.price_ht)}</p>
              </div>
              <div>
                <Label className="text-gray-500">TVA</Label>
                <p className="font-medium">{product.tva_rate}%</p>
              </div>
              <div>
                <Label className="text-gray-500">Prix TTC</Label>
                <p className="font-bold text-lg text-purple-600">
                  {formatCurrency(product.price_ht * (1 + product.tva_rate / 100))}
                </p>
              </div>
            </div>
          </div>

          {/* Stock & Origin */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold mb-3">Stock</h4>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-gray-500">Quantité</Label>
                  <p className="font-bold">{product.stock_quantity}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Min. commande</Label>
                  <p>{product.min_order_quantity || 1}</p>
                </div>
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold mb-3">Origine</h4>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{product.country_flag}</span>
                <div>
                  <p className="font-medium">{product.country_name}</p>
                  {product.region_of_origin && (
                    <p className="text-sm text-gray-500">{product.region_of_origin}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Zones */}
          <div>
            <Label className="text-gray-500">Zones de disponibilité</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {product.available_zones?.map(zone => (
                <Badge key={zone} variant="outline" className="bg-purple-50">
                  {zone}
                </Badge>
              ))}
            </div>
          </div>

          {/* Vendor Info */}
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-4 h-4 text-blue-600" />
              <h4 className="font-semibold text-blue-900">Vendeur</h4>
            </div>
            <p className="text-blue-800">{product.vendor_name || 'N/A'}</p>
            <p className="text-sm text-blue-600">{product.vendor_email || ''}</p>
          </div>

          {/* Rejection Form */}
          {showRejectForm && (
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <Label className="text-red-700">Motif du rejet *</Label>
              <Textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Expliquez pourquoi ce produit est rejeté..."
                className="mt-2"
                rows={3}
              />
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          {product.status === 'pending_approval' && (
            <>
              {!showRejectForm ? (
                <>
                  <Button variant="outline" onClick={() => setShowRejectForm(true)}>
                    <ThumbsDown className="w-4 h-4 mr-2" />
                    Rejeter
                  </Button>
                  <Button 
                    onClick={handleApprove} 
                    disabled={loading}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {loading ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <ThumbsUp className="w-4 h-4 mr-2" />}
                    Approuver
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="outline" onClick={() => setShowRejectForm(false)}>
                    Annuler
                  </Button>
                  <Button 
                    onClick={handleReject} 
                    disabled={loading}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    {loading ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
                    Confirmer le rejet
                  </Button>
                </>
              )}
            </>
          )}
          {product.status !== 'pending_approval' && (
            <Button variant="outline" onClick={onClose}>Fermer</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ===== ADMIN PRODUCTS PAGE =====
