import { Navigate, useLocation } from 'react-router-dom';

// Page fusionnée avec l'Accueil : /kdmarche redirige vers / (ancres conservées).
export default function KdmarchePage() {
  const { hash } = useLocation();
  return <Navigate to={`/${hash || '#pros'}`} replace />;
}
