import { useEffect, useState } from 'react';
import { FileText, FileDown, Loader2, QrCode, CheckCircle2, Clock, PiggyBank, RefreshCw, HandCoins } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { AttestationRcrLedger } from './AttestationRcrLedger';

const dl = async (url, filename) => {
  const r = await fetch(url, { credentials: 'include', headers: getAuthHeaders() });
  if (!r.ok) throw new Error('Téléchargement impossible');
  const blob = await r.blob();
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = filename; a.click();
  URL.revokeObjectURL(u);
};

export const VendorConventionCard = ({ vendorId }) => {
  const [conv, setConv] = useState(null);
  const [atts, setAtts] = useState([]);
  const [busy, setBusy] = useState('');
  const [expanded, setExpanded] = useState(null);

  const loadAtts = () => {
    fetch(`${API}/attestations/vendor/${vendorId}`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : [])).then(setAtts).catch(() => {});
  };

  const isExpiring = (a) => a.status === 'signed' && !a.next_ref && a.date_expiration
    && (new Date(a.date_expiration) - Date.now()) < 30 * 86400000;

  const renew = async (a) => {
    setBusy(a.id);
    try {
      const r = await fetch(`${API}/attestations/${a.id}/renew`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Renouvellement impossible');
      toast.success(`Attestation renouvelée — ${d.new_ref}`, { description: 'En attente de contre-signature O\'SCOP / KDMARCHÉ.' });
      loadAtts();
    } catch (e) { toast.error(e.message); }
    setBusy('');
  };

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API}/convention/vendor/${vendorId}`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setConv).catch(() => {});
    fetch(`${API}/attestations/vendor/${vendorId}`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : [])).then(setAtts).catch(() => {});
  }, [vendorId]);

  if (!conv) return null;
  return (
    <div className="mb-4 rounded-xl p-4 space-y-3"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.3)' }}
      data-testid="vendor-convention-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <FileText className="w-5 h-5 text-[#D9B35A]" />
          <div>
            <p className="text-sm font-bold text-white">Convention cadre tripartite O'SCOP × KDMARCHÉ</p>
            <p className="text-[11px] text-white/50">{conv.ref} · Taux RCR {conv.rcr_rate}% · Plafond global {conv.rcr_global_cap_eur?.toLocaleString('fr-FR')} €</p>
          </div>
        </div>
        <button type="button" data-testid="convention-download-btn" disabled={busy === 'conv'}
          onClick={async () => {
            setBusy('conv');
            try { await dl(`${API}/convention/${conv.id}/pdf`, 'convention-cadre.pdf'); toast.success('Convention téléchargée'); }
            catch (e) { toast.error(e.message); }
            setBusy('');
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold disabled:opacity-50"
          style={{ background: '#D9B35A', color: '#070A10' }}>
          {busy === 'conv' ? <Loader2 size={12} className="animate-spin" /> : <FileDown size={12} />} Télécharger (PDF)
        </button>
      </div>
      {atts.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-white/40 mb-1.5">Attestations nominatives ({atts.length})</p>
          <div className="space-y-1.5">
            {atts.map((a) => (
              <div key={a.id} className="px-3 py-2 rounded-lg bg-white/[0.04] text-xs" data-testid={`attestation-row-${a.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-2.5 text-white/85">
                    {a.status === 'signed' && (
                      <img src={`${API}/attestations/${a.id}/qr.png`} alt="QR de vérification"
                        className="w-11 h-11 rounded bg-white p-0.5" data-testid={`attestation-qr-img-${a.id}`} />
                    )}
                    <span>
                      <b>{a.ref}</b> — {a.product_name}
                      <span className="text-white/45"> · plafond RCR {(a.plafond_cible_cents / 100).toFixed(2)} €</span>
                    </span>
                  </span>
                  <span className="inline-flex items-center gap-2">
                    {a.status === 'signed' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#7BC94E]"><CheckCircle2 size={10} /> Signée (3 parties)</span>
                    ) : a.status === 'closed' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#93C5FD]" data-testid={`attestation-closed-badge-${a.id}`}>
                        <HandCoins size={10} /> Clôturée — RCR remboursée
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#FBBF24]"><Clock size={10} /> Attente contre-signature</span>
                    )}
                    {isExpiring(a) && (
                      <button type="button" disabled={busy === a.id} onClick={() => renew(a)}
                        data-testid={`attestation-renew-btn-${a.id}`}
                        title={`Expire le ${new Date(a.date_expiration).toLocaleDateString('fr-FR')} — renouveler en un clic`}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold disabled:opacity-50"
                        style={{ background: '#D9B35A', color: '#070A10' }}>
                        {busy === a.id ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />} Renouveler
                      </button>
                    )}
                    {a.status === 'closed' && a.reimbursement_id && (
                      <button type="button" data-testid={`attestation-receipt-btn-${a.id}`}
                        title="Reçu de remboursement RCR"
                        onClick={async () => { try { await dl(`${API}/attestations/reimbursements/${a.reimbursement_id}/receipt.pdf`, 'recu-remboursement-rcr.pdf'); } catch (e) { toast.error(e.message); } }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold bg-white/[0.06] text-[#93C5FD]">
                        <FileDown size={11} /> Reçu RCR
                      </button>
                    )}
                    <button type="button" data-testid={`attestation-rcr-toggle-${a.id}`}
                      onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                      title="Suivi des fractions RCR"
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold ${expanded === a.id ? 'bg-[#D9B35A]/20 text-[#E9CF8E]' : 'bg-white/[0.06] text-white/60 hover:text-[#E9CF8E]'}`}>
                      <PiggyBank size={11} /> Suivi RCR
                    </button>
                    <a href={`/verifier-attestation/${a.id}`} target="_blank" rel="noreferrer" title="Page de vérification QR"
                      className="text-white/50 hover:text-[#E9CF8E]" data-testid={`attestation-verify-link-${a.id}`}>
                      <QrCode size={13} />
                    </a>
                    <button type="button" data-testid={`attestation-pdf-${a.id}`}
                      onClick={async () => { try { await dl(`${API}/attestations/${a.id}/pdf`, `${a.ref}.pdf`); } catch (e) { toast.error(e.message); } }}
                      className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={13} /></button>
                  </span>
                </div>
                {expanded === a.id && <AttestationRcrLedger attId={a.id} />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
