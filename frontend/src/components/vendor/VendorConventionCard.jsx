import { useEffect, useState } from 'react';
import { FileText, FileDown, Loader2, QrCode, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

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
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/[0.04] text-xs"
                data-testid={`attestation-row-${a.id}`}>
                <span className="text-white/85">
                  <b>{a.ref}</b> — {a.product_name}
                  <span className="text-white/45"> · plafond RCR {(a.plafond_cible_cents / 100).toFixed(2)} €</span>
                </span>
                <span className="inline-flex items-center gap-2">
                  {a.status === 'signed' ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#7BC94E]"><CheckCircle2 size={10} /> Signée (3 parties)</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#FBBF24]"><Clock size={10} /> Attente contre-signature</span>
                  )}
                  <a href={`/verifier-attestation/${a.id}`} target="_blank" rel="noreferrer" title="Page de vérification QR"
                    className="text-white/50 hover:text-[#E9CF8E]" data-testid={`attestation-verify-link-${a.id}`}>
                    <QrCode size={13} />
                  </a>
                  <button type="button" data-testid={`attestation-pdf-${a.id}`}
                    onClick={async () => { try { await dl(`${API}/attestations/${a.id}/pdf`, `${a.ref}.pdf`); } catch (e) { toast.error(e.message); } }}
                    className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={13} /></button>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
