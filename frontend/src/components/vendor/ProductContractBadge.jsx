import { useState } from 'react';
import { FileSignature, ChevronDown, ChevronUp, FileDown } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const ProductContractBadge = ({ contract, vendorId }) => {
  const [open, setOpen] = useState(false);
  if (!contract) return null;
  const net = (contract.retained_cents || 0) - (contract.released_cents || 0);

  const downloadPdf = async () => {
    try {
      const r = await fetch(`${API_URL}/api/vendor/contracts/${vendorId}/${contract.id}/pdf`);
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${contract.contract_number}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Téléchargement du contrat impossible'); }
  };

  return (
    <div className="mt-2" data-testid={`product-contract-${contract.id}`}>
      <button type="button" onClick={() => setOpen((v) => !v)} data-testid={`product-contract-toggle-${contract.id}`}
        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition-colors">
        <FileSignature className="w-3.5 h-3.5" /> Contrat {contract.contract_number}
        <span className="text-purple-500 font-normal">· garantie {eur(net)}</span>
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && (
        <div className="mt-2 p-3 rounded-lg bg-purple-50/60 border border-purple-100 text-xs space-y-1.5" data-testid={`product-contract-details-${contract.id}`}>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-gray-700">
            <span>Statut : <b>{contract.status === 'ACTIVE' ? 'Actif' : contract.status}</b></span>
            <span>Signé le : <b>{contract.created_at ? new Date(contract.created_at).toLocaleDateString('fr-FR') : '—'}</b></span>
            <span>Taux de rétention : <b>{contract.retention_rate}%</b></span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-gray-700">
            <span>Retenu : <b>{eur(contract.retained_cents)}</b></span>
            <span>Restitué : <b className="text-emerald-700">{eur(contract.released_cents)}</b></span>
            <span>Solde garantie : <b className="text-purple-700">{eur(net)}</b></span>
          </div>
          {(contract.retention_ledger || []).slice(-3).reverse().map((l, i) => (
            <p key={i} className="text-[11px] text-gray-500">
              {l.type === 'RELEASE'
                ? `↩ Restitution de ${eur(l.release_cents)} — ${l.note || ''}`
                : `· Rétention de ${eur(l.retention_cents)} sur ${l.order_number || 'commande'}`}
            </p>
          ))}
          <button type="button" onClick={downloadPdf} data-testid={`product-contract-pdf-${contract.id}`}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold bg-purple-600 text-white hover:bg-purple-700 transition-colors">
            <FileDown className="w-3 h-3" /> Télécharger le contrat PDF
          </button>
        </div>
      )}
    </div>
  );
};
