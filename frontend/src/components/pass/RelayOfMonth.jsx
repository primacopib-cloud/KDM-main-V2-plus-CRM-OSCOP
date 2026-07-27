import { useEffect, useState } from 'react';
import { Trophy, MapPin } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const RelayOfMonth = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    lolodriveAPI.publicRelayOfMonth().then(setData).catch(() => {});
  }, []);
  if (!data || !data.month) return null;
  const label = new Date(`${data.month}-01`).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  return (
    <div className="mb-10 rounded-2xl border border-[#D9B35A]/35 bg-[#D9B35A]/[0.06] p-5 flex flex-wrap items-center gap-4"
      data-testid="relay-of-month">
      {data.photo_url && (
        <img src={data.photo_url} alt={data.name}
          className="w-16 h-16 rounded-xl object-cover border border-[#D9B35A]/40 shrink-0" />
      )}
      <div className="flex-1 min-w-[220px]">
        <p className="text-[11px] uppercase tracking-widest text-[#D9B35A] font-bold flex items-center gap-1.5 mb-1">
          <Trophy className="w-4 h-4" /> Relais du mois — {label}
        </p>
        <p className="text-lg font-bold" data-testid="relay-of-month-name">
          {data.name} <span className="text-white/40 text-sm font-normal">({data.code})</span>
        </p>
        {data.city && (
          <p className="text-xs text-white/50 flex items-center gap-1 mt-0.5">
            <MapPin className="w-3 h-3" /> {data.city}
          </p>
        )}
      </div>
      <p className="text-xs text-white/50 max-w-[240px]">
        Bravo à toute l'équipe du relais, élue meilleure caisse du réseau LOLODRIVE ! 🎉
      </p>
    </div>
  );
};
