import { useEffect, useState } from 'react';
import { CreditCard, Loader2, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '../ui/switch';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const VendorPaymentSettings = ({ vendorId }) => {
  const [cbOnly, setCbOnly] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API_URL}/api/vendor/profile/${vendorId}`)
      .then((r) => r.json())
      .then((d) => setCbOnly(!!d.cb_only_payment))
      .catch(() => setCbOnly(false));
  }, [vendorId]);

  const toggle = async (value) => {
    setSaving(true);
    try {
      const r = await fetch(`${API_URL}/api/vendor/profile/${vendorId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ cb_only_payment: value }),
      });
      if (!r.ok) throw new Error();
      setCbOnly(value);
      toast.success(value
        ? 'Paiement par carte bancaire uniquement activé — vos acheteurs paieront instantanément'
        : 'Tous les modes de paiement sont à nouveau acceptés');
    } catch {
      toast.error('Enregistrement impossible');
    }
    setSaving(false);
  };

  if (cbOnly === null) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mb-6 flex flex-wrap items-center gap-4"
      data-testid="vendor-payment-settings">
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: '#D9B35A1c', border: '1px solid #D9B35A55' }}>
        <CreditCard className="w-5 h-5 text-[#D9B35A]" />
      </div>
      <div className="flex-1 min-w-[240px]">
        <p className="font-semibold text-white m-0 flex items-center gap-2">
          Paiement par carte bancaire uniquement
          {cbOnly && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold text-[#1F0A33]"
              style={{ background: '#8CC63E' }} data-testid="vendor-cb-only-badge">
              <Zap className="w-3 h-3" /> Paiement instantané
            </span>
          )}
        </p>
        <p className="text-xs text-white/55 m-0 mt-1">
          Activé : vos acheteurs règlent leur commande instantanément par carte — le règlement à réception
          et le paiement échelonné sont désactivés pour vos produits.
        </p>
      </div>
      <div className="flex items-center gap-2">
        {saving && <Loader2 className="w-4 h-4 animate-spin text-white/50" />}
        <Switch checked={cbOnly} onCheckedChange={toggle} disabled={saving}
          data-testid="vendor-cb-only-switch" />
      </div>
    </div>
  );
};
