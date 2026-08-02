import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Loader2, PackageCheck, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

// Bloc « Mon plafond à réception » — espace acheteur
export const RarCeilingBlock = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showStatuses, setShowStatuses] = useState(false);

  const load = () => rarAPI.myStatus().then(setData).catch(() => {});
  useEffect(() => { load(); }, []);

  const request = async () => {
    setBusy(true);
    try {
      const r = await rarAPI.requestAccess('');
      toast.success(r.message || 'Demande envoyée');
      load();
    } catch (e) { toast.error(e.message || 'Erreur'); } finally { setBusy(false); }
  };

  const viaPack = async () => {
    setBusy(true);
    try {
      const r = await rarAPI.activateViaPack();
      toast.success(r.message || 'Éligibilité activée !');
      load();
    } catch (e) { toast.error(e.message || 'Aucun pack CREDI\'SCOP trouvé'); } finally { setBusy(false); }
  };

  if (!data) return null;
  const rows = [
    ['Plafond accordé', data.ceiling_cents, 'text-white'],
    ['Commandes en préparation', data.preparation_cents, 'text-amber-300'],
    ['Commandes en livraison', data.delivery_cents, 'text-sky-300'],
    ['Paiements en traitement', data.processing_cents, 'text-purple-300'],
    ['Plafond immédiatement disponible', data.available_cents, 'text-emerald-300 font-bold'],
  ];
  return (
    <div className="rounded-2xl p-5 border border-[#D9B35A]/30" data-testid="rar-ceiling-block"
      style={{ background: 'linear-gradient(120deg, rgba(217,179,90,0.10), rgba(255,255,255,0.02))' }}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 m-0">
          <ShieldCheck className="w-4 h-4 text-[#D9B35A]" /> Mon plafond à réception
        </h3>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
          data.status === 'APPROVED' ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'
            : data.status === 'PENDING' ? 'text-amber-300 bg-amber-400/10 border-amber-400/30'
              : data.status === 'SUSPENDED' ? 'text-red-300 bg-red-400/10 border-red-400/30'
                : 'text-white/50 bg-white/5 border-white/15'}`} data-testid="rar-status-badge">
          {{ APPROVED: 'Compte validé', PENDING: 'Demande en cours d\'instruction', SUSPENDED: 'Suspendu', REJECTED: 'Refusée', NONE: 'Non activé' }[data.status] || data.status}
        </span>
      </div>

      {data.status === 'APPROVED' ? (
        <>
          <div className="space-y-1.5" data-testid="rar-amounts-table">
            {rows.map(([label, cents, cls]) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-white/60">{label}</span>
                <span className={`font-mono ${cls}`}>{fmt(cents)}</span>
              </div>
            ))}
          </div>
          <button type="button" onClick={() => setShowStatuses(!showStatuses)} data-testid="rar-statuses-toggle"
            className="mt-3 text-[10px] text-white/45 hover:text-white/70 flex items-center gap-1">
            Statuts des commandes {showStatuses ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {showStatuses && (
            <div className="mt-2 flex flex-wrap gap-1">
              {(data.statuses || []).map((s) => (
                <span key={s} className="px-2 py-0.5 rounded-full text-[9px] text-white/55 bg-white/[0.04] border border-white/10">{s}</span>
              ))}
            </div>
          )}
          <p className="text-[10px] text-white/35 mt-2">
            Le plafond est rétabli après confirmation effective du paiement (encaissement définitif), non à la signature du bon de livraison.
          </p>
        </>
      ) : data.status === 'PENDING' ? (
        <p className="text-xs text-white/60">
          Votre demande est en cours d'instruction par KDMARCHÉ. Accès sous réserve d'éligibilité et de plafond disponible.
        </p>
      ) : (
        <>
          <p className="text-xs text-white/60 mb-3">
            Commandez sans acompte sur les marchandises éligibles — le règlement est déclenché après validation
            électronique de la réception. <b>Accès sous réserve d'éligibilité et de plafond disponible.</b>
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={request} disabled={busy} data-testid="rar-request-btn"
              className="px-3 py-2 rounded-lg text-xs font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] disabled:opacity-50 flex items-center gap-1.5">
              {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
              Demander l'accès
            </button>
            <button type="button" onClick={viaPack} disabled={busy} data-testid="rar-pack-btn"
              className="px-3 py-2 rounded-lg text-xs font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 hover:bg-emerald-400/20 disabled:opacity-50 flex items-center gap-1.5">
              <PackageCheck className="w-3 h-3" /> Éligibilité immédiate via pack CREDI'SCOP
            </button>
            <Link to="/wallet" className="px-3 py-2 rounded-lg text-xs text-white/60 border border-white/15 hover:text-white">
              Acheter un pack CREDI'SCOP
            </Link>
          </div>
        </>
      )}
    </div>
  );
};
