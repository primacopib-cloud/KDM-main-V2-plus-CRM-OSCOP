import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { REJECTION_REASONS } from './adminV2Constants';

export const DecisionDialog = ({
  decisionDialogOpen, setDecisionDialogOpen, selectedApp, decisionType,
  rejectionReason, setRejectionReason, decisionComment, setDecisionComment,
  submittingDecision, handleDecision,
}) => (
      <Dialog open={decisionDialogOpen} onOpenChange={setDecisionDialogOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {decisionType === 'APPROVED' ? (
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-400" />
              )}
              {decisionType === 'APPROVED' ? 'Approuver la demande' : 'Rejeter la demande'}
            </DialogTitle>
            <DialogDescription className="text-white/60">
              {selectedApp?.org?.legal_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {decisionType === 'REJECTED' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Raison du rejet *</label>
                <Select value={rejectionReason} onValueChange={setRejectionReason}>
                  <SelectTrigger className="w-full bg-white/[0.04] border-white/10">
                    <SelectValue placeholder="Sélectionner une raison" />
                  </SelectTrigger>
                  <SelectContent>
                    {REJECTION_REASONS.map(reason => (
                      <SelectItem key={reason.code} value={reason.code}>
                        {reason.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Commentaire (optionnel)</label>
              <Textarea
                placeholder="Ajouter un commentaire..."
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                className="bg-white/[0.04] border-white/10"
                rows={3}
              />
            </div>

            {decisionType === 'APPROVED' && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-sm text-green-400">
                  L'approbation va créer automatiquement :
                </p>
                <ul className="text-xs text-green-400/80 mt-1 space-y-1">
                  <li>• Un wallet avec crédits initiaux</li>
                  <li>• L'accès à la zone du territoire</li>
                  <li>• Le compte partenaire KDMARCHE</li>
                </ul>
              </div>
            )}
          </div>

          <DialogFooter className="flex gap-3">
            <Button 
              variant="outline" 
              onClick={() => setDecisionDialogOpen(false)}
              className="border-white/10"
            >
              Annuler
            </Button>
            <Button
              onClick={handleDecision}
              disabled={submittingDecision || (decisionType === 'REJECTED' && !rejectionReason)}
              className={decisionType === 'APPROVED' 
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-red-500 hover:bg-red-600 text-white'
              }
            >
              {submittingDecision ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : decisionType === 'APPROVED' ? (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              ) : (
                <XCircle className="w-4 h-4 mr-2" />
              )}
              {decisionType === 'APPROVED' ? 'Confirmer l\'approbation' : 'Confirmer le rejet'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
);
