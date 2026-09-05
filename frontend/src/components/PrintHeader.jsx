import { useEffect, useState } from 'react';
import { partners } from '../data/mock';

export const PrintHeader = () => {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const update = () => setNow(new Date());
    window.addEventListener('beforeprint', update);
    return () => window.removeEventListener('beforeprint', update);
  }, []);
  const date = now.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const time = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  return (
    <div className="print-header" data-testid="print-header">
      <img src={partners.oscop.logo} alt="O'SCOP" />
      <div>
        <strong>SCIC SAS OBJECTIF SCOP OUTREMER — Super Admin</strong>
        <span>Imprimé le {date} à {time}</span>
      </div>
    </div>
  );
};
