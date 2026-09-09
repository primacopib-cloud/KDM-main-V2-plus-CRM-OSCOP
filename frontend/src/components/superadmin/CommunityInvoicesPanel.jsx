import { useEffect, useState } from 'react';
import { Receipt, Download, Loader2, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

// Historique des factures de publication CommunityPlace (acquittées) + re-téléchargement PDF
export const CommunityInvoicesPanel = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/communityplace/invoices`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => toast.error('Erreur de chargement des factures'));
  }, []);

  const download = async (inv) => {
    setBusy(inv.id);
    try {
      const r = await fetch(`${API}/admin/communityplace/invoices/${inv.id}/pdf`, {
        headers: getAuthHeaders(), credentials: 'include',
      });
      if (!r.ok) throw new Error('Téléchargement impossible');
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `facture-${inv.reference}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  const exportCsv = () => {
    const header = ['Facture', 'Type', 'Société', 'Contact', 'Email', 'Produit', 'Payée le', 'Montant EUR'];
    const lines = data.invoices.map((i) => [
      `CP-${i.reference}`, i.listing_type === 'OFFRE' ? 'Offre' : 'Demande', i.company, i.contact_name,
      i.email, i.product, String(i.communityplace_paid_at || '').slice(0, 10),
      Number(i.communityplace_fee_eur || 0).toFixed(2)]);
    const csv = [header, ...lines]
      .map((l) => l.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(';')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `factures-publication-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="rounded-[18px] p-5 mt-6 bg-white/[0.04] border border-white/10" data-testid="community-invoices-panel">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-sm font-bold text-white m-0 flex items-center gap-2">
          <Receipt className="w-4 h-4 text-[#D9B35A]" /> Factures de publication émises
          {data && <span className="text-white/40 font-normal">({data.invoices.length})</span>}
        </h3>
        <div className="flex items-center gap-3">
          {data && <span className="text-xs font-bold text-[#8CC63E]">Total encaissé : {data.total_eur.toFixed(2)} €</span>}
          {data && data.invoices.length > 0 && (
            <button type="button" onClick={exportCsv} data-testid="invoices-export-csv"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] border border-white/15 text-white/75 hover:text-white">
              <FileDown className="w-3.5 h-3.5" /> Exporter CSV
            </button>
          )}
        </div>
      </div>
      {!data ? (
        <div className="py-5 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-white/40" /></div>
      ) : data.invoices.length === 0 ? (
        <p className="text-xs text-white/40 py-2 m-0">Aucune facture émise pour le moment — elles apparaîtront après chaque paiement de publication.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-white/40 border-b border-white/10">
                <th className="py-2 pr-3">Facture</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Client</th>
                <th className="py-2 pr-3">Produit</th>
                <th className="py-2 pr-3">Payée le</th>
                <th className="py-2 pr-3">Montant</th>
                <th className="py-2">PDF</th>
              </tr>
            </thead>
            <tbody>
              {data.invoices.map((inv) => (
                <tr key={inv.id || inv.reference} className="border-b border-white/5" data-testid={`invoice-row-${inv.reference}`}>
                  <td className="py-2 pr-3 font-mono text-xs text-white/80">CP-{inv.reference}</td>
                  <td className="py-2 pr-3">
                    <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                      inv.listing_type === 'OFFRE' ? 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40' : 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'}`}>
                      {inv.listing_type === 'OFFRE' ? 'Offre' : 'Demande'}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-white/70 text-xs">{inv.company || inv.contact_name}<br /><span className="text-white/40">{inv.email}</span></td>
                  <td className="py-2 pr-3 text-white/70 text-xs">{inv.product}</td>
                  <td className="py-2 pr-3 text-white/50 text-xs">{String(inv.communityplace_paid_at || '').slice(0, 10)}</td>
                  <td className="py-2 pr-3 text-[#8CC63E] font-bold text-xs">{Number(inv.communityplace_fee_eur || 0).toFixed(2)} €</td>
                  <td className="py-2">
                    <button type="button" onClick={() => download(inv)} disabled={busy === inv.id}
                      data-testid={`invoice-download-${inv.reference}`} title="Télécharger le PDF"
                      className="p-1.5 rounded-md bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/25">
                      {busy === inv.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
