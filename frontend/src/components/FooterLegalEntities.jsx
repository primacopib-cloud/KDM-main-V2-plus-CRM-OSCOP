import { useEffect, useState } from 'react';

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export const FooterLegalEntities = () => {
  const [legal, setLegal] = useState(null);
  useEffect(() => {
    fetch(`${BACKEND}/api/public/sale-model/config`)
      .then((r) => r.json())
      .then((d) => setLegal(d.legal))
      .catch(() => {});
  }, []);

  const line = (e) => {
    if (!e) return null;
    const parts = [e.name];
    if (e.legal_form) parts.push(e.legal_form);
    if (e.siret) parts.push(`SIRET ${e.siret}`);
    if (e.rcs) parts.push(`RCS ${e.rcs}`);
    if (e.vat) parts.push(`TVA ${e.vat}`);
    return parts.join(' — ');
  };

  if (!legal) {
    return (
      <p className="text-white/40 text-[11px] mt-1" data-testid="footer-legal-entity">
        KDMARCHÉ, service exploité par PRIMACOP INTERNATIONAL BUSINESS — SIRET 433 230 703 00020
      </p>
    );
  }
  return (
    <div className="mt-1 space-y-0.5" data-testid="footer-legal-entity">
      <p className="text-white/40 text-[11px]">{line(legal.partner)}</p>
      <p className="text-white/40 text-[11px]" data-testid="footer-legal-oscop">{line(legal.oscop)}</p>
      <p className="text-white/30 text-[10px]">
        Deux circuits transparents : vente partenaire directe • achat-revente O'SCOP — le vendeur-facturier est identifié sur chaque offre.
      </p>
    </div>
  );
};
