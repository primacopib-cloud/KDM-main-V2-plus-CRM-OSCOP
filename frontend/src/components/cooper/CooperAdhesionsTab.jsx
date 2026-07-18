import { useState, useEffect, useCallback } from 'react';
import { Loader2, Check, X, Building2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall, apiCallV2 } from '../../services/http';

export const CooperAdhesionsTab = () => {
  const [apps, setApps] = useState(null);

  const load = useCallback(() => {
    apiCall('/cooper/adhesions').then((d) => setApps(d.applications)).catch((e) => {
      toast.error(e.message || 'Erreur de chargement');
      setApps([]);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  const decide = async (appId, decision) => {
    try {
      await apiCallV2(`/applications/${appId}/decision`, {
        method: 'POST',
        body: JSON.stringify({ decision, reason_code: decision === 'APPROVED' ? 'OK' : 'REFUS_COOPER', comment: `Décision COOPER : ${decision}` }),
      });
      toast.success(decision === 'APPROVED' ? 'Adhésion validée — membre inscrit au registre' : 'Adhésion rejetée');
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  if (apps === null) return <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#6FA82E]" /></div>;

  return (
    <div className="space-y-3" data-testid="cooper-adhesions-tab">
      {apps.length === 0 ? (
        <div className="glass-panel-soft rounded-[18px] p-8 text-center text-sm opacity-60" data-testid="cooper-adhesions-empty">
          Aucune demande d'adhésion en attente de validation.
        </div>
      ) : apps.map((a) => (
        <div key={a.id} className="glass-panel-soft rounded-[18px] p-4 flex flex-wrap items-center gap-4" data-testid={`cooper-adhesion-${a.id}`}>
          <Building2 className="w-8 h-8 text-[#6FA82E] flex-shrink-0" />
          <div className="flex-1 min-w-[220px]">
            <p className="font-semibold text-sm">{a.org?.legal_name}</p>
            <p className="text-xs opacity-60">
              SIRET {a.org?.registration_id} · {a.org?.territory} ·{' '}
              <span className="font-semibold text-[#B8860B]">{a.org?.member_type === 'VENDOR_PRO' ? 'Vendeur pro' : 'Acheteur pro'}</span>
              {' '}· déposée le {new Date(a.created_at).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => decide(a.id, 'APPROVED')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#6FA82E]/15 text-[#4d7a1c] border border-[#6FA82E]/40 hover:bg-[#6FA82E]/25 transition-colors"
              data-testid={`cooper-approve-${a.id}`}>
              <Check className="w-3.5 h-3.5" /> Valider l'adhésion
            </button>
            <button onClick={() => decide(a.id, 'REJECTED')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-red-500/10 text-red-600 border border-red-500/30 hover:bg-red-500/20 transition-colors"
              data-testid={`cooper-reject-${a.id}`}>
              <X className="w-3.5 h-3.5" /> Rejeter
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
