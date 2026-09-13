import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API, getAuthHeaders } from '../services/http';

// Lien inter-espaces : affiché uniquement si le membre détient l'abonnement Pro cible actif
// (requireFlag = "has_buyer_pro" pour le lien Espace Acheteur, "has_vendor_pro" pour Espace Vendeur).
export const CrossSpaceLink = ({ to, requireFlag, testId, className, children }) => {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    fetch(`${API}/member/space-access`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setAllowed(Boolean(d && d[requireFlag])))
      .catch(() => {});
  }, [requireFlag]);

  if (!allowed) return null;
  return (
    <Link to={to} data-testid={testId} className={className}>
      {children}
    </Link>
  );
};
