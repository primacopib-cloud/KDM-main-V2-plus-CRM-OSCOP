import { useEffect, useState } from 'react';
import { FileSignature, Loader2, Download, BellRing, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { AdhesionFunnel } from './AdhesionFunnel';
import { AdhesionReminders } from './AdhesionReminders';

const STATUS = {
  PAYMENT_PENDING: { color: '#9CA3AF', label: 'Paiement en attente' },
  PAID: { color: '#60A5FA', label: 'Payé — infos à compléter' },
  INFO_COMPLETED: { color: '#FBBF24', label: 'À signer' },
  SIGNED: { color: '#E9CF8E', label: 'Signé — activation en attente' },
  ACTIVATED: { color: '#7BC94E', label: 'Actif' },
};
const SUB = {
  active: { color: '#7BC94E', label: 'Abonnement actif' },
  past_due: { color: '#F87171', label: 'Impayé' },
  unpaid: { color: '#F87171', label: 'Impayé' },
  canceled: { color: '#9CA3AF', label: 'Résilié' },
};

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');

export const VendorAdhesionsPanel = () => {
  const [items, setItems] = useState(null);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  const load = () => {
    fetch(`${API}/vendor-onboarding/admin/list`, opts)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const remind = async (oid) => {
    try {
      const r = await fetch(`${API}/vendor-onboarding/admin/${oid}/remind`, { method: 'POST', ...opts });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Relance impossible');
      toast.success(`Relance ${d.kind} envoyée`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (items === null) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /></div>;

  return (
    <>
      <AdhesionFunnel />
      <div className="glass-panel-soft rounded-[18px] p-4 mb-5" data-testid="vendor-adhesions-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <FileSignature className="w-4 h-4" /> Adhésions — conventions & abonnements
        </h3>
        <div className="flex items-center gap-1.5">
          <button type="button" data-testid="adhesions-export-csv"
            onClick={async () => {
              try {
                const r = await fetch(`${API}/vendor-onboarding/admin/export.csv`, opts);
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'adhesions.csv'; a.click();
                URL.revokeObjectURL(url);
              } catch { toast.error("Échec de l'export"); }
            }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold"
            style={{ background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.4)' }}>
            <Download className="w-3 h-3" /> Export CSV
          </button>
          <button type="button" onClick={load} className="p-1.5 rounded-lg border border-white/15 text-white/60 hover:text-white" title="Rafraîchir">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-white/40">Aucune adhésion vendeur pour le moment.</p>
      ) : (
        <div className="space-y-1.5 max-h-96 overflow-y-auto">
          {items.map((ob) => {
            const st = STATUS[ob.status] || STATUS.PAYMENT_PENDING;
            const sub = ob.subscription_status ? (SUB[ob.subscription_status] || null) : null;
            return (
              <div key={ob.id} className="flex flex-wrap items-center gap-2.5 px-3 py-2 rounded-lg bg-white/[0.04] text-xs"
                data-testid={`adhesion-row-${ob.id}`}>
                <div className="min-w-[160px] flex-1">
                  <p className="text-white/90 font-medium">{ob.company}</p>
                  <p className="text-white/45">{ob.contact_name} · {ob.email} · {fmt(ob.created_at)}</p>
                </div>
                <span className="text-white/55">{ob.plan_name}</span>
                <span className="font-semibold px-2 py-0.5 rounded-full" style={{ color: st.color, background: `${st.color}1c` }}>
                  {st.label}
                </span>
                {sub && (
                  <span className="font-semibold px-2 py-0.5 rounded-full" style={{ color: sub.color, background: `${sub.color}1c` }}>
                    {sub.label}
                  </span>
                )}
                <div className="flex gap-1.5 ml-auto">
                  {['SIGNED', 'ACTIVATED'].includes(ob.status) && (
                    <a href={`${API}/vendor-onboarding/${ob.id}/convention.pdf`} target="_blank" rel="noreferrer"
                      title="Convention signée (PDF)" data-testid={`adhesion-convention-${ob.id}`}
                      className="p-1.5 rounded-lg text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15">
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  )}
                  {ob.status !== 'ACTIVATED' && (
                    <button type="button" onClick={() => remind(ob.id)} title="Relancer par email"
                      data-testid={`adhesion-remind-${ob.id}`}
                      className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg font-bold"
                      style={{ background: 'rgba(217,179,90,0.16)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.45)' }}>
                      <BellRing className="w-3 h-3" /> Relancer
                    </button>
                  )}
                </div>
                <AdhesionReminders ob={ob} />
              </div>
            );
          })}
        </div>
      )}
      </div>
    </>
  );
};
