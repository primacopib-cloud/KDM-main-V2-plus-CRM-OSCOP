import { useState, useEffect, useCallback } from 'react';
import { FileSignature, Loader2, Undo2, MapPin, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../../services/http';
import { ConventionRegistres } from './ConventionRegistres';

const eur = (cents) => `${((cents || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

const ContractRow = ({ c, onRelease }) => {
  const [open, setOpen] = useState(false);
  const net = (c.retained_cents || 0) - (c.released_cents || 0);
  const pct = Math.min(100, Math.round(((c.retained_cents || 0) / c.retention_cap_cents) * 100));
  return (
    <div className="rounded-2xl bg-white border border-[#E9DCC0] overflow-hidden" data-testid={`admin-contract-${c.contract_number}`}>
      <div className="p-4 flex flex-wrap items-center gap-4">
        <FileSignature className="w-7 h-7 text-[#4C2A6E] flex-shrink-0" />
        <div className="flex-1 min-w-[240px]">
          <p className="font-semibold text-sm text-[#3D2E1E]">{c.product_name} <span className="text-[#8A785F] font-normal">— {c.vendor_name}</span></p>
          <p className="text-xs text-[#8A785F]">{c.contract_number} · {c.territory} · signé le {new Date(c.created_at).toLocaleDateString('fr-FR')}</p>
          <div className="mt-1.5 flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full bg-[#F3E9D2] overflow-hidden max-w-[220px]">
              <div className="h-full bg-[#D9B35A]" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs text-[#7A6850]">
              Retenu {eur(c.retained_cents)} · Restitué {eur(c.released_cents)} · <strong className="text-[#4C2A6E]">Solde {eur(net)}</strong>
            </span>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          {net > 0 && (
            <button onClick={() => onRelease(c, net)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-green-500/10 text-green-700 border border-green-500/30 hover:bg-green-500/20 transition-colors"
              data-testid={`contract-release-${c.contract_number}`}>
              <Undo2 className="w-3.5 h-3.5" /> Restituer
            </button>
          )}
          {(c.retention_ledger || []).length > 0 && (
            <button onClick={() => setOpen(!open)} className="p-2 rounded-lg text-[#8A785F] hover:bg-[#FBF6EC]" data-testid={`contract-ledger-${c.contract_number}`}>
              {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>
      {open && (
        <div className="px-5 pb-4 text-xs text-[#5C4B36] space-y-1 bg-[#FBF6EC]">
          <p className="pt-2 text-[11px] font-bold uppercase text-[#8A785F]">Registre du contrat</p>
          {c.retention_ledger.map((l, i) => (
            <p key={`${c.id}-l${i}`}>
              {l.type === 'RELEASE'
                ? <>↩ Restitution de <strong>{eur(l.release_cents)}</strong> — {new Date(l.at).toLocaleString('fr-FR')} — par {l.by} — {l.note}</>
                : <>• Rétention de <strong>{eur(l.retention_cents)}</strong> sur facture {l.order_number || l.order_id} — {new Date(l.at).toLocaleString('fr-FR')}</>}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

export const AdminContractsTab = () => {
  const [data, setData] = useState(null);

  const load = useCallback(() => {
    apiCall('/vendor/contracts/admin/all').then(setData).catch((e) => {
      toast.error(e.message || 'Erreur de chargement');
      setData({ contracts: [], by_territory: {}, total_net_cents: 0 });
    });
  }, []);
  useEffect(() => { load(); }, [load]);

  const release = async (c, maxCents) => {
    const amountStr = window.prompt(`Montant à restituer sur ${c.contract_number} (max ${(maxCents / 100).toFixed(2)} €) :`, (maxCents / 100).toFixed(2));
    if (amountStr === null) return;
    const cents = Math.round(parseFloat(amountStr.replace(',', '.')) * 100);
    if (!cents || cents <= 0) { toast.error('Montant invalide'); return; }
    const note = window.prompt('Motif de la restitution (obligatoire, ex: « Bonne exécution du contrat ») :');
    if (!note || note.trim().length < 3) { if (note !== null) toast.error('Motif obligatoire'); return; }
    try {
      await apiCall(`/vendor/contracts/admin/${c.id}/release`, {
        method: 'POST', body: JSON.stringify({ amount_cents: cents, note: note.trim() }),
      });
      toast.success(`${(cents / 100).toFixed(2)} € restitués — tracé au registre du contrat`);
      load();
    } catch (e) {
      toast.error(e.message || 'Erreur');
    }
  };

  if (!data) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>;

  return (
    <div className="space-y-5" data-testid="admin-contracts-tab">
      <ConventionRegistres />
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2 text-[#4C2A6E]">
          <FileSignature className="w-5 h-5 text-[#D9B35A]" /> Contrats d'engagement de volume
          <span className="text-sm font-normal text-[#8A785F]">— garanties nettes détenues : <strong className="text-[#4C2A6E]" data-testid="contracts-total-net">{eur(data.total_net_cents)}</strong></span>
        </h2>
        <button
          onClick={async () => {
            try {
              const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vendor/contracts/admin/report-pdf`, { credentials: 'include' });
              if (!r.ok) throw new Error('Export impossible');
              const blob = await r.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `etat-garanties-${new Date().toISOString().slice(0, 10)}.pdf`;
              a.click();
              URL.revokeObjectURL(url);
              toast.success('État des garanties PDF téléchargé');
            } catch (e) { toast.error(e.message); }
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-white text-[#4C2A6E] border border-[#E9DCC0] hover:border-[#D9B35A]/50 transition-colors"
          data-testid="contracts-report-pdf-btn">
          <FileText className="w-3.5 h-3.5" /> Rapport garanties PDF
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="contracts-territories">
        {Object.entries(data.by_territory).map(([terr, t]) => (
          <div key={terr} className="rounded-2xl bg-white border border-[#E9DCC0] p-4 shadow-[0_4px_16px_rgba(76,42,110,0.06)]">
            <p className="text-xs text-[#8A785F] flex items-center gap-1.5 mb-1"><MapPin className="w-3.5 h-3.5 text-[#D9B35A]" /> {terr}</p>
            <p className="text-xl font-bold text-[#4C2A6E]">{eur(t.net_cents)}</p>
            <p className="text-[11px] text-[#A8977C]">{t.contracts} contrat(s) · retenu {eur(t.retained_cents)} · restitué {eur(t.released_cents)}</p>
          </div>
        ))}
      </div>

      {data.contracts.length === 0 ? (
        <div className="rounded-2xl bg-white border border-[#E9DCC0] p-10 text-center text-sm text-[#8A785F]" data-testid="contracts-empty">
          Aucun contrat — ils sont générés automatiquement à la validation des produits vendeurs.
        </div>
      ) : (
        <div className="space-y-3">
          {data.contracts.map((c) => <ContractRow key={c.id} c={c} onRelease={release} />)}
        </div>
      )}
    </div>
  );
};
