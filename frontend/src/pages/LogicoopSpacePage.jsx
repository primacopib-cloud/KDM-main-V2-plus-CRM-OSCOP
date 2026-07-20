import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Truck, Warehouse, Ship, ArrowLeft } from 'lucide-react';
import { BrandLogos } from '../components/BrandLogos';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function LogicoopSpacePage() {
  const [op, setOp] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/logicoop/me`, { credentials: 'include' })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) setError(d.detail || 'Accès refusé');
        else setOp(d);
      })
      .catch(() => setError('Connexion requise'));
  }, []);

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }} data-testid="logicoop-space-page">
      <header className="sticky top-0 z-50" style={{ background: 'rgba(30,12,52,0.9)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(212,175,55,0.32)' }}>
        <div className="max-w-[1160px] mx-auto px-5 py-3 flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" /><span className="text-sm hidden sm:inline">Retour</span>
          </Link>
          <BrandLogos size="sm" />
          <span className="ml-auto inline-flex items-center gap-2 text-sm font-bold text-[#E9CF8E]">
            <Truck className="w-4 h-4" /> Espace LOGICOOP
          </span>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-10">
        {error && (
          <div className="glass-panel-soft rounded-[18px] p-8 text-center" data-testid="logicoop-denied">
            <Truck className="w-10 h-10 text-[#D9B35A] mx-auto mb-3" />
            <h1 className="text-xl font-bold text-white mb-2">Espace réservé aux opérateurs LOGICOOP</h1>
            <p className="text-sm text-white/55">{error}. Connectez-vous avec un compte opérateur, ou candidatez via le formulaire « Devenir partenaire » en pied de page.</p>
          </div>
        )}
        {op && (
          <div data-testid="logicoop-dashboard">
            <h1 className="text-2xl font-bold text-white mb-1">Bienvenue, {op.name}</h1>
            <p className="text-sm text-white/55 mb-8">Vos zones opérationnelles assignées par la coopérative.</p>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="glass-panel-soft rounded-[18px] p-5" data-testid="logicoop-exw-zones">
                <h2 className="font-display text-lg text-white flex items-center gap-2 mb-3">
                  <Warehouse className="w-4 h-4 text-[#D9B35A]" /> Zones entrepôt EXW ({op.exw_zones_detail.length})
                </h2>
                {op.exw_zones_detail.map((z) => (
                  <div key={z.code} className="flex items-center gap-2 py-2 border-b border-white/[0.06]">
                    <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E]">{z.code}</span>
                    <span className="text-sm text-white/85">{z.name}</span>
                  </div>
                ))}
                {!op.exw_zones_detail.length && <p className="text-sm text-white/45">Aucune zone EXW assignée.</p>}
              </div>
              <div className="glass-panel-soft rounded-[18px] p-5" data-testid="logicoop-cif-zones">
                <h2 className="font-display text-lg text-white flex items-center gap-2 mb-3">
                  <Ship className="w-4 h-4 text-[#D9B35A]" /> Zones livraison CIF ({op.cif_zones_detail.length})
                </h2>
                {op.cif_zones_detail.map((z) => (
                  <div key={z.code} className="flex items-center gap-2 py-2 border-b border-white/[0.06]">
                    <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#60A5FA]/20 text-[#60A5FA]">{z.code}</span>
                    <span className="text-sm text-white/85">{z.name}</span>
                  </div>
                ))}
                {!op.cif_zones_detail.length && <p className="text-sm text-white/45">Aucune zone CIF assignée.</p>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
