import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trophy, BadgeCheck, MapPin, Users } from 'lucide-react';
import { Flag } from '../components/Flag';
import { detaillantAPI } from '../services/api.detaillant';

export default function PopsLeaderboardPage() {
  const [shops, setShops] = useState(null);
  const [country, setCountry] = useState('');
  const [category, setCategory] = useState('');
  useEffect(() => { detaillantAPI.shopsPublic().then((d) => setShops(d.shops || [])).catch(() => setShops([])); }, []);

  const facets = useMemo(() => {
    const countries = [...new Set((shops || []).map((s) => s.country_code).filter(Boolean))].sort();
    const cats = [...new Set((shops || []).flatMap((s) => s.categories || []))].sort();
    return { countries, cats };
  }, [shops]);

  const visible = useMemo(() => (shops || []).filter((s) =>
    (!country || s.country_code === country) &&
    (!category || (s.categories || []).includes(category))), [shops, country, category]);

  if (!shops) return <div className="min-h-screen bg-[#1F0A33] text-white" />;
  return (
    <div className="min-h-screen bg-[#1F0A33] text-white px-4 sm:px-8 py-10" data-testid="pops-leaderboard-page">
      <div className="max-w-3xl mx-auto">
        <Link to="/detaillant" className="text-xs text-white/50 hover:text-[#E9CF8E]">← Retour à la vitrine POP'S</Link>
        <h1 className="text-3xl sm:text-4xl font-black mt-4 flex items-center gap-3">
          <Trophy className="w-8 h-8 text-[#FFD700]" /> Palmarès des POP'S
        </h1>
        <p className="text-sm text-white/60 mt-2">
          Les boutiques — <b>P</b>artenaire d'<b>O</b>ffres de <b>P</b>roduits <b>S</b>olidaires — classées selon les avis des Coop'acteurs après chaque enlèvement.
        </p>

        <div className="flex flex-wrap gap-1.5 mt-5" data-testid="pops-lb-filters">
          {facets.countries.map((cc) => (
            <button key={cc} onClick={() => setCountry(country === cc ? '' : cc)}
              data-testid={`pops-lb-country-${cc}`}
              className={`inline-flex items-center gap-1.5 px-2.5 h-7 rounded-full text-[11px] font-bold border transition-colors ${country === cc ? 'border-[#D9B35A] bg-[#D9B35A]/20 text-[#E9CF8E]' : 'border-white/15 text-white/55 hover:border-white/40'}`}>
              <Flag code={cc} /> {cc}
            </button>
          ))}
          {facets.cats.length > 0 && facets.cats.map((c) => (
            <button key={c} onClick={() => setCategory(category === c ? '' : c)}
              data-testid={`pops-lb-cat-${c}`}
              className={`px-2.5 h-7 rounded-full text-[11px] font-bold border transition-colors ${category === c ? 'border-emerald-400 bg-emerald-500/20 text-emerald-300' : 'border-white/15 text-white/55 hover:border-white/40'}`}>
              {c}
            </button>
          ))}
        </div>

        {visible.length === 0 && <p className="text-sm text-white/40 mt-8" data-testid="pops-lb-empty">Aucun POP'S ne correspond à ces filtres.</p>}
        <div className="space-y-3 mt-6">
          {visible.map((s, i) => (
            <Link key={s.user_id} to={`/pops/${s.user_id}`}
              className={`flex items-center gap-3 rounded-2xl border p-4 transition-colors ${i === 0 && !country && !category ? 'border-[#FFD700]/60 bg-[#FFD700]/[0.06]' : 'border-white/10 bg-white/[0.03]'} hover:border-[#D9B35A]/60`}
              data-testid={`pops-lb-row-${s.user_id}`}>
              <span className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-black shrink-0 ${i === 0 && !country && !category ? 'bg-gradient-to-br from-[#FFD700] to-[#D9B35A] text-[#1F0A33]' : 'bg-white/[0.06] text-white/60'}`}>
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold truncate" data-testid={`pops-lb-name-${i}`}>{s.company_name}</span>
                  {i === 0 && !country && !category && s.gold && (
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-black bg-gradient-to-r from-[#FFD700] to-[#D9B35A] text-[#1F0A33]">🏆 POP'S d'Or</span>
                  )}
                  {s.rating_count > 0 && (
                    <span className="text-[10px] font-bold text-amber-300">★ {Number(s.rating_avg).toFixed(1)} ({s.rating_count})</span>
                  )}
                  {s.rating_count === 0 && <span className="text-[10px] text-white/35">Pas encore noté</span>}
                </div>
                <p className="text-[11px] text-white/45 flex items-center gap-1 mt-0.5">
                  <MapPin className="w-3 h-3" /> {s.locality || '—'} <Flag code={s.country_code} />
                  {(s.categories || []).length > 0 && <span className="text-white/35">· {(s.categories || []).join(', ')}</span>}
                </p>
              </div>
              <BadgeCheck className="w-4 h-4 text-white/25 shrink-0" />
            </Link>
          ))}
        </div>
        <p className="text-[10px] text-white/35 mt-6 flex items-center gap-1">
          <Users className="w-3 h-3" /> Le palmarès évolue à chaque avis déposé après un enlèvement.
        </p>
      </div>
    </div>
  );
}
