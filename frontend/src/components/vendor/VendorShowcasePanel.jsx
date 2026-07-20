import { useEffect, useState } from 'react';
import { Images } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Switch } from '../ui/switch';

const API = process.env.REACT_APP_BACKEND_URL;

export const VendorShowcasePanel = ({ vendorId }) => {
  const [optIn, setOptIn] = useState(null);
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API}/api/showcase/vendor-opt-in/${vendorId}`)
      .then((r) => r.json())
      .then((d) => { setOptIn(!!d.opt_in); setApproved(!!d.approved); })
      .catch(() => {});
  }, [vendorId]);

  const toggle = async (value) => {
    setOptIn(value);
    const r = await fetch(`${API}/api/showcase/vendor-opt-in/${vendorId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ opt_in: value }),
    });
    if (!r.ok) { setOptIn(!value); return toast.error('Mise à jour impossible'); }
    toast.success(value
      ? "Votre logo apparaît désormais dans la vitrine de la page d'accueil"
      : 'Votre logo est retiré de la vitrine');
  };

  if (optIn === null) return null;

  return (
    <Card data-testid="vendor-showcase-panel">
      <CardContent className="py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <Images className="w-5 h-5 text-purple-600 mt-0.5" />
          <div>
            <p className="font-semibold text-sm">Apparaître dans la vitrine partenaires</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Votre logo (photo principale de vos produits) rejoint automatiquement le carrousel
              « Ils nous font confiance » de la page d'accueil.
              {!approved && ' Disponible dès validation de votre compte vendeur.'}
            </p>
          </div>
        </div>
        <Switch checked={optIn} onCheckedChange={toggle} disabled={!approved} data-testid="vendor-showcase-switch" />
      </CardContent>
    </Card>
  );
};
