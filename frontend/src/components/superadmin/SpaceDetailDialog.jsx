import { useEffect, useState } from 'react';
import { Loader2, UserCog } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { API, getAuthHeaders } from '../../services/http';
import { TerritoryFlag } from '../Flag';

const euros = (c) => `${((c || 0) / 100).toFixed(2)} €`;
const d10 = (s) => (s ? String(s).slice(0, 10) : '—');

export const SpaceDetailDialog = ({ open, onClose, kind, row, spaceLabel }) => {
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!open || !row) return;
    setDetail(null);
    fetch(`${API}/admin/spaces/${kind}/${row.id}/detail`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setDetail)
      .catch(() => toast.error('Erreur de chargement de la fiche'));
  }, [open, kind, row]);

  const p = detail?.profile || {};
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#1F0A33] border-white/15 text-white max-w-lg max-h-[85vh] overflow-y-auto" data-testid="space-detail-dialog">
        <DialogHeader>
          <DialogTitle className="text-white">Fiche {spaceLabel} — {row?.name}</DialogTitle>
        </DialogHeader>
        {!detail ? (
          <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-white/40" /></div>
        ) : (
          <div className="space-y-4 text-sm">
            <div className="rounded-xl p-3 bg-white/[0.04] border border-white/10 grid grid-cols-2 gap-2 text-xs">
              <div><span className="text-white/40">Email</span><p className="text-white/85">{p.email || '—'}</p></div>
              <div><span className="text-white/40">Téléphone</span><p className="text-white/85">{p.phone || '—'}</p></div>
              <div><span className="text-white/40">Pays</span>
                <p className="text-white/85 flex items-center gap-1.5">
                  {p.country ? <><TerritoryFlag territory={p.country} className="w-4 h-auto rounded-[1px] inline-block" />{p.country}</> : '—'}
                </p></div>
              <div><span className="text-white/40">Statut</span><p className="text-white/85">{p.status || '—'}</p></div>
              <div><span className="text-white/40">Inscrit le</span><p className="text-white/85">{d10(p.created_at)}</p></div>
              {p.detail && <div><span className="text-white/40">Détail</span><p className="text-white/85">{p.detail}</p></div>}
            </div>

            {detail.passes.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase text-white/45 mb-1.5">PASS LOLODRIVE</h4>
                {detail.passes.map((pa, i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 border-b border-white/5">
                    <span className="text-white/80">{d10(pa.starts_at)} → {d10(pa.ends_at)}</span>
                    <span className="text-white/60">{pa.uc_granted ? `${Math.round(pa.uc_granted / 100)} UC` : ''} · {pa.status}</span>
                  </div>
                ))}
              </div>
            )}

            {detail.orders.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase text-white/45 mb-1.5">Historique commandes</h4>
                {detail.orders.map((o, i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 border-b border-white/5" data-testid={`detail-order-${i}`}>
                    <span className="text-white/80">{o.order_number || '—'} · {d10(o.date)}</span>
                    <span className="text-white/60">{euros(o.total_cents)} · {o.status}</span>
                  </div>
                ))}
              </div>
            )}
            {detail.orders.length === 0 && kind !== 'vendors' && kind !== 'investors' && (
              <p className="text-xs text-white/35">Aucune commande enregistrée</p>
            )}

            {detail.extra.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase text-white/45 mb-1.5">{kind === 'vendors' ? 'Produits' : 'Informations'}</h4>
                {detail.extra.map((x, i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 border-b border-white/5">
                    <span className="text-white/80">{x.label}</span><span className="text-white/60">{x.value}</span>
                  </div>
                ))}
              </div>
            )}

            {detail.activity.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase text-white/45 mb-1.5">Activité</h4>
                {detail.activity.map((a, i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 border-b border-white/5">
                    <span className="text-white/80">{a.label}</span><span className="text-white/50">{d10(a.date)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export const RelayManagerDialog = ({ open, onClose, relay, onLinked }) => {
  const [managers, setManagers] = useState(null);
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/admin/spaces/relays/managers`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { setManagers(d.managers); setEmail(d.managers[0]?.email || ''); })
      .catch(() => toast.error('Erreur de chargement des gérants'));
  }, [open]);

  const link = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/admin/spaces/relays/${relay.id}/manager`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ email }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Gérant lié au relais ${relay.name}`);
      onLinked();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#1F0A33] border-white/15 text-white max-w-md" data-testid="relay-manager-dialog">
        <DialogHeader>
          <DialogTitle className="text-white flex items-center gap-2"><UserCog className="w-4 h-4 text-[#D9B35A]" /> Lier un gérant — {relay?.name}</DialogTitle>
        </DialogHeader>
        {!managers ? (
          <div className="py-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-white/40" /></div>
        ) : managers.length === 0 ? (
          <p className="text-sm text-white/50">Aucun compte gérant (rôle GERANT_LOLO_POINT) disponible.</p>
        ) : (
          <div className="space-y-2">
            <label className="text-xs text-white/60">Compte gérant</label>
            <select value={email} onChange={(e) => setEmail(e.target.value)} data-testid="relay-manager-select"
              className="w-full bg-white/[0.05] border border-white/15 rounded-md px-3 py-2 text-sm text-white">
              {managers.map((m) => (
                <option key={m.id} value={m.email} className="bg-[#1F0A33]">{m.name} — {m.email}</option>
              ))}
            </select>
            <p className="text-[11px] text-white/40">Le gérant sera connecté à ce relais (email de contact + compte).</p>
          </div>
        )}
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} className="text-white/60">Annuler</Button>
          <Button onClick={link} disabled={busy || !email} data-testid="relay-manager-confirm"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lier le gérant'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
