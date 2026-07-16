import {
  CreditCard, CheckCircle2, Loader2, ShoppingCart, Sparkles,
  Building2, Landmark, Copy, CheckCheck, FileText, Lock, AlertCircle,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

const PackageGrid = ({ packages, selectedPackage, onSelect, compact = false }) => (
  <div className="grid sm:grid-cols-2 gap-3">
    {packages.map((pkg) => (
      compact ? (
        <div
          key={pkg.id}
          className={`p-3 rounded-xl border cursor-pointer transition-all ${
            selectedPackage?.id === pkg.id
              ? 'bg-[#D9B35A]/20 border-[#D9B35A]'
              : 'bg-white/[0.02] border-white/[0.08] hover:border-white/20'
          }`}
          onClick={() => onSelect(pkg)}
        >
          <div className="flex justify-between items-center">
            <span className="font-medium">{pkg.name}</span>
            <span className="text-[#D9B35A] font-bold">{pkg.price}€</span>
          </div>
          <p className="text-xs text-white/50">{pkg.credits} crédits</p>
        </div>
      ) : (
        <div
          key={pkg.id}
          className={`relative p-4 rounded-xl border transition-all cursor-pointer hover:scale-[1.01] ${
            selectedPackage?.id === pkg.id
              ? 'bg-[#D9B35A]/20 border-[#D9B35A]'
              : pkg.popular
                ? 'bg-[#D9B35A]/5 border-[#D9B35A]/30'
                : 'bg-white/[0.02] border-white/[0.08] hover:border-white/20'
          }`}
          onClick={() => onSelect(pkg)}
          data-testid={`package-${pkg.id}`}
        >
          {pkg.popular && (
            <Badge className="absolute -top-2 right-2 bg-[#D9B35A] text-black text-xs">
              <Sparkles className="w-3 h-3 mr-1" />Populaire
            </Badge>
          )}
          <h4 className="font-semibold text-white/90">{pkg.name}</h4>
          <p className="text-xs text-white/50 mb-2">{pkg.description}</p>
          <div className="flex items-end justify-between">
            <span className="text-xl font-bold text-[#D9B35A]">{pkg.credits} <span className="text-sm font-normal text-white/40">crédits</span></span>
            <span className="text-lg font-semibold">{pkg.price}€</span>
          </div>
        </div>
      )
    ))}
  </div>
);

const TransferReferenceView = ({ transferReference, bankDetails, copiedField, copyToClipboard }) => (
  <div className="space-y-4">
    <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
      <div className="flex items-center gap-2 mb-2">
        <CheckCircle2 className="w-5 h-5 text-green-400" />
        <span className="font-semibold text-green-400">Référence générée</span>
      </div>
      <p className="text-sm text-white/70">Effectuez le virement avec les informations ci-dessous</p>
    </div>

    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-3">
      <div className="flex justify-between items-center">
        <span className="text-white/60 text-sm">Montant</span>
        <span className="font-bold text-xl text-[#D9B35A]">{transferReference.amount}€</span>
      </div>

      <div className="pt-3 border-t border-white/[0.08]">
        <div className="flex justify-between items-center mb-1">
          <span className="text-white/60 text-sm">Référence à indiquer</span>
          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(transferReference.reference, 'ref')} className="h-6 px-2">
            {copiedField === 'ref' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          </Button>
        </div>
        <code className="block p-2 rounded bg-black/30 text-[#D9B35A] text-sm font-mono">{transferReference.reference}</code>
      </div>

      <div className="pt-3 border-t border-white/[0.08] space-y-2">
        <p className="text-white/60 text-sm font-medium">Coordonnées bancaires</p>

        <div className="flex justify-between items-center">
          <span className="text-xs text-white/50">Bénéficiaire</span>
          <span className="text-sm">{bankDetails?.account_holder}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-white/50">IBAN</span>
          <div className="flex items-center gap-1">
            <code className="text-sm font-mono">{bankDetails?.iban}</code>
            <Button variant="ghost" size="sm" onClick={() => copyToClipboard(bankDetails?.iban?.replace(/\s/g, ''), 'iban')} className="h-5 w-5 p-0">
              {copiedField === 'iban' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            </Button>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-white/50">BIC</span>
          <div className="flex items-center gap-1">
            <code className="text-sm font-mono">{bankDetails?.bic}</code>
            <Button variant="ghost" size="sm" onClick={() => copyToClipboard(bankDetails?.bic, 'bic')} className="h-5 w-5 p-0">
              {copiedField === 'bic' ? <CheckCheck className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            </Button>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-white/50">Banque</span>
          <span className="text-sm">{bankDetails?.bank_name} - {bankDetails?.branch}</span>
        </div>
      </div>
    </div>

    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
      <p className="text-xs text-amber-400">
        <AlertCircle className="w-3 h-3 inline mr-1" />
        Vos crédits seront ajoutés après validation du virement (1-3 jours ouvrés)
      </p>
    </div>
  </div>
);

export const BuyCreditsDialog = ({
  open, onOpenChange, packages, selectedPackage, setSelectedPackage,
  paymentMethod, setPaymentMethod, checkoutLoading, onCardPayment,
  companyName, setCompanyName, onBankTransfer, transferReference, bankDetails,
  copiedField, copyToClipboard,
  sepaIban, setSepaIban, sepaName, setSepaName, sepaEmail, setSepaEmail,
  sepaLoading, onSepaSetup,
}) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto bg-[#0a0d14] border-white/10 text-white">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
          Acheter des crédits
        </DialogTitle>
        <DialogDescription className="text-white/50">
          Choisissez votre mode de paiement et sélectionnez un pack
        </DialogDescription>
      </DialogHeader>

      <Tabs value={paymentMethod} onValueChange={setPaymentMethod} className="mt-2">
        <TabsList className="grid grid-cols-3 bg-white/[0.04] border border-white/[0.08]">
          <TabsTrigger value="card" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
            <CreditCard className="w-4 h-4 mr-2" />
            Carte
          </TabsTrigger>
          <TabsTrigger value="transfer" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
            <Landmark className="w-4 h-4 mr-2" />
            Virement
          </TabsTrigger>
          <TabsTrigger value="sepa" className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]">
            <Building2 className="w-4 h-4 mr-2" />
            SEPA B2B
          </TabsTrigger>
        </TabsList>

        {/* Card Payment Tab */}
        <TabsContent value="card" className="mt-4">
          <PackageGrid packages={packages} selectedPackage={selectedPackage} onSelect={setSelectedPackage} />
          <Button
            onClick={() => selectedPackage && onCardPayment(selectedPackage)}
            disabled={!selectedPackage || checkoutLoading}
            className="w-full mt-4 bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
          >
            {checkoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />}
            Payer par carte {selectedPackage && `(${selectedPackage.price}€)`}
          </Button>
          <p className="text-xs text-center text-white/40 mt-2">
            <Lock className="w-3 h-3 inline mr-1" />Paiement sécurisé par Stripe
          </p>
        </TabsContent>

        {/* Bank Transfer Tab */}
        <TabsContent value="transfer" className="mt-4">
          {!transferReference ? (
            <>
              <div className="mb-4">
                <Label className="text-white/70">Nom de l&apos;entreprise (pour la référence)</Label>
                <Input
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Ex: Ma Société SAS"
                  className="mt-1 bg-white/[0.04] border-white/10"
                />
              </div>
              <PackageGrid packages={packages} selectedPackage={selectedPackage} onSelect={setSelectedPackage} compact />
              <Button
                onClick={() => selectedPackage && onBankTransfer(selectedPackage)}
                disabled={!selectedPackage || !companyName.trim() || checkoutLoading}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
              >
                {checkoutLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FileText className="w-4 h-4 mr-2" />}
                Générer référence de virement
              </Button>
            </>
          ) : (
            <TransferReferenceView
              transferReference={transferReference}
              bankDetails={bankDetails}
              copiedField={copiedField}
              copyToClipboard={copyToClipboard}
            />
          )}
        </TabsContent>

        {/* SEPA Direct Debit Tab */}
        <TabsContent value="sepa" className="mt-4">
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-xs text-blue-400">
                <Building2 className="w-3 h-3 inline mr-1" />
                Le prélèvement SEPA B2B permet des paiements récurrents automatiques
              </p>
            </div>

            <div className="grid gap-3">
              <div>
                <Label className="text-white/70">IBAN</Label>
                <Input
                  value={sepaIban}
                  onChange={(e) => setSepaIban(e.target.value.toUpperCase())}
                  placeholder="FR76 XXXX XXXX XXXX XXXX XXXX XXX"
                  className="mt-1 bg-white/[0.04] border-white/10 font-mono"
                />
              </div>
              <div>
                <Label className="text-white/70">Titulaire du compte</Label>
                <Input
                  value={sepaName}
                  onChange={(e) => setSepaName(e.target.value)}
                  placeholder="Nom de l'entreprise ou du titulaire"
                  className="mt-1 bg-white/[0.04] border-white/10"
                />
              </div>
              <div>
                <Label className="text-white/70">Email (pour le mandat)</Label>
                <Input
                  type="email"
                  value={sepaEmail}
                  onChange={(e) => setSepaEmail(e.target.value)}
                  placeholder="comptabilite@entreprise.fr"
                  className="mt-1 bg-white/[0.04] border-white/10"
                />
              </div>
            </div>

            <PackageGrid packages={packages} selectedPackage={selectedPackage} onSelect={setSelectedPackage} compact />

            <Button
              onClick={() => selectedPackage && onSepaSetup(selectedPackage)}
              disabled={!selectedPackage || !sepaIban || !sepaName || !sepaEmail || sepaLoading}
              className="w-full bg-purple-600 hover:bg-purple-700"
            >
              {sepaLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Building2 className="w-4 h-4 mr-2" />}
              Configurer le prélèvement SEPA
            </Button>

            <p className="text-xs text-center text-white/40">
              En continuant, vous autorisez O&apos;SCOP à débiter votre compte via SEPA
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </DialogContent>
  </Dialog>
);
