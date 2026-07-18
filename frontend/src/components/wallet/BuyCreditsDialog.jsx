import { CreditCard, Loader2, Lock, ShoppingCart, Check } from 'lucide-react';
import { Button } from '../ui/button';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../ui/dialog';

const PackageGrid = ({ packages, selectedPackage, onSelect }) => (
  <div className="grid sm:grid-cols-3 gap-3">
    {packages.map((pkg) => (
      <button
        key={pkg.id}
        onClick={() => onSelect(pkg)}
        data-testid={`credit-pack-${pkg.id}`}
        className={`p-4 rounded-xl border text-left transition-all ${
          selectedPackage?.id === pkg.id
            ? 'bg-[#D9B35A]/15 border-[#D9B35A]/50'
            : 'bg-white/[0.04] border-white/[0.08] hover:border-white/20'
        }`}
      >
        <div className="flex items-center justify-between mb-1">
          <p className="font-semibold text-white/90 text-sm">{pkg.name}</p>
          {selectedPackage?.id === pkg.id && <Check className="w-4 h-4 text-[#D9B35A]" />}
        </div>
        <p className="text-2xl font-bold text-[#D9B35A]">{pkg.credits}<span className="text-xs font-normal text-white/50 ml-1">crédits</span></p>
        <p className="text-sm text-white/60 mt-1">{pkg.price}€</p>
      </button>
    ))}
  </div>
);

export const BuyCreditsDialog = ({
  open, onOpenChange, packages, selectedPackage, setSelectedPackage,
  checkoutLoading, onCardPayment,
}) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-[640px] max-h-[90vh] overflow-y-auto bg-[#0a0d14] border-white/10 text-white">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
          Acheter des crédits
        </DialogTitle>
        <DialogDescription className="text-white/50">
          Paiement exclusivement par carte bancaire — sélectionnez un pack
        </DialogDescription>
      </DialogHeader>

      <div className="mt-2">
        <PackageGrid packages={packages} selectedPackage={selectedPackage} onSelect={setSelectedPackage} />
        <Button
          onClick={() => selectedPackage && onCardPayment(selectedPackage)}
          disabled={!selectedPackage || checkoutLoading}
          className="w-full mt-4 bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
          data-testid="buy-credits-card-btn"
        >
          {checkoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />}
          Payer par carte {selectedPackage && `(${selectedPackage.price}€)`}
        </Button>
        <p className="text-xs text-center text-white/40 mt-2">
          <Lock className="w-3 h-3 inline mr-1" />Paiement sécurisé par carte bancaire via Stripe
        </p>
      </div>
    </DialogContent>
  </Dialog>
);
