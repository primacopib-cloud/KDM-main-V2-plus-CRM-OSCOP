import { useState, useEffect } from 'react';
import { FileSignature, Loader2, FileDown, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const VendorContractsTab = ({ vendorId }) => {
  const [contracts, setContracts] = useState(null);

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API_URL}/api/vendor/contracts/${vendorId}`)
      .then((r) => r.json())
      .then((d) => setContracts(d.contracts))
      .catch(() => setContracts([]));
  }, [vendorId]);

  const downloadPdf = async (c) => {
    try {
      const r = await fetch(`${API_URL}/api/vendor/contracts/${vendorId}/${c.id}/pdf`);
      if (!r.ok) throw new Error('Téléchargement impossible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${c.contract_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (contracts === null) return <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-purple-600" /></div>;

  return (
    <div className="space-y-4" data-testid="vendor-contracts-tab">
      <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 text-sm text-purple-900">
        <ShieldCheck className="w-4 h-4 inline mr-1.5" />
        Chaque produit référencé génère automatiquement un <strong>contrat cadre d'engagement de volume</strong> :
        une rétention de garantie de <strong>5 % sur facture</strong> est constituée jusqu'à un plafond de
        <strong> 20 000 €</strong>, restituable en cas de bonne exécution.
      </div>

      {contracts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileSignature className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucun contrat pour le moment</h3>
            <p className="text-gray-500">Vos contrats seront générés automatiquement dès la validation de vos produits.</p>
          </CardContent>
        </Card>
      ) : contracts.map((c) => {
        const pct = Math.min(100, Math.round((c.retained_cents / c.retention_cap_cents) * 100));
        return (
          <Card key={c.id} data-testid={`vendor-contract-${c.contract_number}`}>
            <CardContent className="py-4 flex flex-wrap items-center gap-4">
              <FileSignature className="w-8 h-8 text-purple-600 flex-shrink-0" />
              <div className="flex-1 min-w-[220px]">
                <p className="font-semibold text-sm text-gray-900">{c.product_name}</p>
                <p className="text-xs text-gray-500">
                  {c.contract_number} · engagement {c.volume_commitment} {c.unit} · signé le {new Date(c.created_at).toLocaleDateString('fr-FR')} ·{' '}
                  <span className={`font-semibold ${c.status === 'ACTIVE' ? 'text-green-600' : 'text-gray-500'}`}>{c.status}</span>
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden max-w-[280px]">
                    <div className="h-full bg-amber-500" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-gray-600" data-testid={`contract-retention-${c.contract_number}`}>
                    Rétention {(c.retained_cents / 100).toFixed(2)} € / {(c.retention_cap_cents / 100).toLocaleString('fr-FR')} € ({c.retention_rate} %)
                  </span>
                </div>
              </div>
              <button onClick={() => downloadPdf(c)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 text-white hover:bg-purple-700 transition-colors"
                data-testid={`contract-pdf-${c.contract_number}`}>
                <FileDown className="w-3.5 h-3.5" /> Contrat PDF
              </button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
