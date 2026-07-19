import { useEffect, useState } from 'react';
import { FileText, Download, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

export const VendorInvoicesTab = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/vendor/my-invoices`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const download = async (number) => {
    try {
      const r = await fetch(`${API}/api/vendor/my-invoices/${number}/pdf`, { credentials: 'include' });
      if (!r.ok) return toast.error('Téléchargement impossible');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = `${number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Facture ${number} téléchargée`);
    } catch {
      toast.error('Téléchargement impossible');
    }
  };

  if (loading) {
    return <div className="py-12 text-center"><RefreshCw className="w-6 h-6 animate-spin text-purple-600 mx-auto" /></div>;
  }

  return (
    <div className="space-y-3" data-testid="vendor-invoices-tab">
      {!items.length && (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune facture</h3>
            <p className="text-gray-500">Vos factures d'adhésion et de renouvellement apparaîtront ici automatiquement.</p>
          </CardContent>
        </Card>
      )}
      {items.map((inv) => (
        <Card key={inv.number} className="hover:shadow-md transition-shadow" data-testid={`invoice-row-${inv.number}`}>
          <CardContent className="p-4 flex flex-wrap items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <p className="font-semibold text-gray-900">{inv.number}</p>
              <p className="text-sm text-gray-500">{inv.label} · {String(inv.date).slice(0, 10)}</p>
            </div>
            <div className="text-right mr-2">
              <p className="font-bold text-gray-900">{eur(inv.ttc_cents)} TTC</p>
              <p className="text-xs text-gray-500">dont TVA {inv.vat_rate}% : {eur(inv.vat_cents)}</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => download(inv.number)} className="gap-1.5" data-testid={`invoice-download-${inv.number}`}>
              <Download className="w-4 h-4" /> PDF
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
