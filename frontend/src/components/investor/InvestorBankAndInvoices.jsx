import { useState, useEffect, useCallback, useRef } from 'react';
import { Landmark, FileText, Download, Upload, CheckCircle2, CreditCard, Euro } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const downloadBlob = async (url, filename) => {
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Téléchargement impossible');
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href; a.download = filename; a.click();
  URL.revokeObjectURL(href);
};

// Coordonnées bancaires (IBAN/BIC + RIB PDF/PNG) de l'investisseur
export const InvestorBankDetails = () => {
  const [form, setForm] = useState({ holder: '', iban: '', bic: '' });
  const [hasRib, setHasRib] = useState(false);
  const [ribStatus, setRibStatus] = useState(null);
  const [saved, setSaved] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    fetch(`${API_URL}/api/investor-plans/bank-details`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        if (d.bank_details) { setForm({ holder: d.bank_details.holder || '', iban: d.bank_details.iban || '', bic: d.bank_details.bic || '' }); setSaved(!!d.bank_details.iban); setRibStatus(d.bank_details.rib_status || null); }
        setHasRib(d.has_rib);
        setLoaded(true);
      }).catch(() => setLoaded(true));
  }, []);
  useEffect(load, [load]);

  const save = async () => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/bank-details`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      toast.success('Coordonnées bancaires enregistrées');
      setSaved(true);
    } catch (e) { toast.error(e.message); }
  };

  const uploadRib = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error('Fichier trop volumineux (max 5 Mo)'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const res = await fetch(`${API_URL}/api/investor-plans/bank-details/rib`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify({ filename: file.name, content_base64: reader.result.split(',')[1] }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
        toast.success('RIB téléversé — en attente de validation');
        setHasRib(true);
        setRibStatus('PENDING');
      } catch (e) { toast.error(e.message); }
    };
    reader.readAsDataURL(file);
  };

  const openCardPortal = async () => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/billing-portal`, { method: 'POST', headers: getAuthHeaders() });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Portail indisponible');
      window.location.href = d.portal_url;
    } catch (e) { toast.error(e.message); }
  };

  if (!loaded) return null;
  const incomplete = !saved || !hasRib;
  const RIB_CHIP = { PENDING: ['En attente de validation', 'text-amber-300 bg-amber-500/10 border-amber-400/40'], APPROVED: ['RIB approuvé', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'], REJECTED: ['RIB refusé — retéléversez', 'text-red-300 bg-red-500/10 border-red-400/40'] };
  const chip = hasRib && RIB_CHIP[ribStatus];
  return (
    <div className="rounded-[20px] p-5 mb-5 bg-white/[0.03] border border-[#D9B35A]/25" data-testid="investor-bank-details">
      <div className="flex items-center gap-2 mb-2">
        <Landmark className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Mes coordonnées bancaires (remboursements)</h3>
        {chip && <span className={`ml-auto px-2 py-0.5 rounded-full border text-[10px] font-semibold ${chip[1]}`} data-testid="rib-status-chip">{chip[0]}</span>}
        {saved && hasRib && ribStatus === 'APPROVED' && <CheckCircle2 className="w-4 h-4 text-[#8CC63E]" data-testid="bank-details-complete" />}
      </div>
      {incomplete && (
        <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-400/40 rounded-xl px-3 py-2 mb-3" data-testid="bank-details-invitation">
          Merci de renseigner vos coordonnées bancaires et de téléverser votre RIB (PDF ou PNG) : ils sont
          indispensables au versement de vos remboursements d'investissement.
        </p>
      )}
      <div className="grid gap-2 sm:grid-cols-3 mb-2">
        <input value={form.holder} onChange={(e) => setForm({ ...form, holder: e.target.value })}
          placeholder="Titulaire du compte" data-testid="bank-holder-input"
          className="h-9 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
        <input value={form.iban} onChange={(e) => setForm({ ...form, iban: e.target.value })}
          placeholder="IBAN" data-testid="bank-iban-input"
          className="h-9 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs font-mono" />
        <input value={form.bic} onChange={(e) => setForm({ ...form, bic: e.target.value })}
          placeholder="BIC / SWIFT" data-testid="bank-bic-input"
          className="h-9 px-3 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs font-mono" />
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <button type="button" onClick={save} data-testid="bank-details-save"
          className="px-3 py-1.5 rounded-lg text-xs font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">
          Enregistrer
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.png" className="hidden"
          onChange={(e) => uploadRib(e.target.files?.[0])} data-testid="rib-file-input" />
        <button type="button" onClick={() => fileRef.current?.click()} data-testid="rib-upload-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
          <Upload className="w-3.5 h-3.5" /> {hasRib ? 'Remplacer mon RIB' : 'Téléverser mon RIB (PDF/PNG)'}
        </button>
        {hasRib && (
          <button type="button" data-testid="rib-download-btn"
            onClick={() => downloadBlob(`${API_URL}/api/investor-plans/bank-details/rib`, 'mon-rib').catch((e) => toast.error(e.message))}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white/70 bg-white/[0.05] border border-white/15 hover:bg-white/[0.1] transition-colors">
            <Download className="w-3.5 h-3.5" /> Mon RIB
          </button>
        )}
        <button type="button" onClick={openCardPortal} data-testid="card-portal-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
          <CreditCard className="w-3.5 h-3.5" /> Mettre à jour ma carte bancaire
        </button>
      </div>
      <MyRepayments />
    </div>
  );
};

// Remboursements versés sur l'IBAN + relevé annuel fiscal
const MyRepayments = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/api/investor-plans/my-repayments`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData).catch(() => {});
  }, []);
  const year = new Date().getFullYear();
  return (
    <div className="mt-4 pt-3 border-t border-white/[0.08]" data-testid="my-repayments">
      <div className="flex items-center gap-2 mb-2">
        <Euro className="w-3.5 h-3.5 text-[#8CC63E]" />
        <h4 className="text-xs font-bold text-[#E9CF8E] m-0">Remboursements versés {data ? `(total ${(data.total_eur ?? 0).toLocaleString('fr-FR')} €)` : ''}</h4>
        <button type="button" data-testid="annual-statement-btn"
          onClick={() => downloadBlob(`${API_URL}/api/investor-plans/my-annual-statement/${year}/pdf`, `releve-annuel-${year}.pdf`).catch((e) => toast.error(e.message))}
          className="ml-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
          <FileText className="w-3 h-3" /> Relevé annuel {year}
        </button>
      </div>
      {!data?.repayments?.length ? (
        <p className="text-[11px] text-white/40 m-0">Aucun remboursement versé pour le moment.</p>
      ) : (
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {data.repayments.map((r) => (
            <div key={r.id} className="flex items-center gap-3 text-xs text-white/70" data-testid={`repayment-row-${r.reference}`}>
              <span className="font-mono text-white/40 w-20 shrink-0">{new Date(r.paid_at).toLocaleDateString('fr-FR')}</span>
              <span className="flex-1 truncate">Réf. {r.reference}{r.operation_ref ? ` — ${r.operation_ref}` : ''} · IBAN …{(r.iban || '').slice(-4)}</span>
              <span className="font-mono text-[#8CC63E] font-bold">+{(r.amount_eur ?? 0).toLocaleString('fr-FR')} €</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Archive des factures mensuelles d'abonnement
export const InvestorInvoicesArchive = () => {
  const [invoices, setInvoices] = useState([]);
  useEffect(() => {
    fetch(`${API_URL}/api/investor-plans/my-invoices`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setInvoices(d.invoices || [])).catch(() => {});
  }, []);
  if (!invoices.length) return null;
  return (
    <div className="rounded-[20px] p-5 mb-5 bg-white/[0.03] border border-white/[0.08]" data-testid="investor-invoices-archive">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Mes factures d'abonnement ({invoices.length})</h3>
      </div>
      <div className="space-y-1.5 max-h-52 overflow-y-auto">
        {invoices.map((inv) => (
          <div key={inv.id} className="flex items-center gap-3 text-xs text-white/70" data-testid={`invoice-row-${inv.number}`}>
            <span className="font-mono text-white/40 w-20 shrink-0">{inv.period_label}</span>
            <span className="flex-1 truncate">{inv.number} — plan {inv.plan_code}</span>
            <span className="font-mono">{(inv.amount_eur ?? 0).toLocaleString('fr-FR')} €</span>
            <button type="button" data-testid={`invoice-download-${inv.number}`}
              onClick={() => downloadBlob(`${API_URL}/api/investor-plans/my-invoices/${inv.id}/pdf`, `${inv.number}.pdf`).catch((e) => toast.error(e.message))}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
              <Download className="w-3 h-3" /> PDF
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
