import { Plus, Globe, CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';

export const TopupDialog = ({ open, onOpenChange, amount, setAmount, loading, onSubmit }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Plus className="w-5 h-5 text-[#D9B35A]" />
          Recharger mon CREDI&rsquo;SCOP
        </DialogTitle>
        <DialogDescription className="text-white/60">
          Ajoutez des crédits à votre compte O&apos;SCOP
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Montant (crédits)</label>
          <Input
            type="number"
            min={10}
            step={10}
            value={amount}
            onChange={(e) => setAmount(parseInt(e.target.value) || 0)}
            className="bg-white/[0.04] border-white/10 text-xl font-bold text-center"
          />
        </div>

        <div className="flex gap-2">
          {[50, 100, 200, 500].map(quick => (
            <button
              key={quick}
              onClick={() => setAmount(quick)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                amount === quick
                  ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
                  : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
              }`}
            >
              {quick}
            </button>
          ))}
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
          <p className="text-xs text-white/50">
            Les crédits sont non remboursables et non convertibles en espèces.
            Ils permettent d&apos;accéder aux services premium O&apos;SCOP.
          </p>
        </div>
      </div>

      <DialogFooter className="flex gap-3">
        <Button variant="outline" onClick={() => onOpenChange(false)} className="border-white/10">
          Annuler
        </Button>
        <Button
          onClick={onSubmit}
          disabled={loading || amount < 10}
          className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
          ) : (
            <Plus className="w-4 h-4 mr-2" />
          )}
          Ajouter {amount} crédits
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

export const ZoneAddDialog = ({ open, onOpenChange, selectedZone, loading, onSubmit, onCancel }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-[#D4AF37]" />
          Activer une zone
        </DialogTitle>
        <DialogDescription className="text-white/60">
          {selectedZone
            ? `Activer l'accès à ${selectedZone.name}`
            : 'Sélectionnez une zone à activer'
          }
        </DialogDescription>
      </DialogHeader>

      {selectedZone && (
        <div className="py-4">
          <div className="p-4 rounded-xl bg-[#D4AF37]/5 border border-[#D4AF37]/20">
            <p className="font-semibold text-white/90">{selectedZone.name}</p>
            <p className="text-sm text-white/60 mt-1">{selectedZone.code}</p>
            {selectedZone.exw_only && (
              <p className="text-xs text-amber-400 mt-2">
                ⚠️ Cette zone fonctionne en Incoterm EXW uniquement
              </p>
            )}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
            <p className="text-xs text-white/50">
              L&apos;activation d&apos;une zone vous permet d&apos;accéder aux prix et de passer
              des commandes pour les produits disponibles dans cette zone.
            </p>
          </div>
        </div>
      )}

      <DialogFooter className="flex gap-3">
        <Button variant="outline" onClick={onCancel} className="border-white/10">
          Annuler
        </Button>
        <Button
          onClick={onSubmit}
          disabled={loading || !selectedZone}
          className="bg-[#D4AF37] hover:bg-[#47c18a] text-black"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
          ) : (
            <CheckCircle2 className="w-4 h-4 mr-2" />
          )}
          Activer la zone
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);
