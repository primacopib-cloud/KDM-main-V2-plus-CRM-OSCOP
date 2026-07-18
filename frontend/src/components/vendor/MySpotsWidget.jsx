import { useState, useEffect } from 'react';
import { Clapperboard, Eye, Trophy } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const LANG_LABELS = { fr: '🇫🇷', en: '🇬🇧', es: '🇪🇸' };

export const MySpotsWidget = ({ vendorId }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/vendor/ai/spots/${vendorId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setData(d))
      .catch(() => {});
  }, [vendorId]);

  if (!data || !data.total_spots) return null;

  return (
    <Card data-testid="my-spots-widget">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Clapperboard className="w-5 h-5 text-purple-600" /> Mes spots vidéo
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="rounded-xl bg-purple-50 border border-purple-100 p-3 text-center" data-testid="spots-total">
            <p className="text-2xl font-bold text-purple-700">{data.total_spots}</p>
            <p className="text-[11px] uppercase tracking-wider text-purple-600/70">Spots créés</p>
          </div>
          <div className="rounded-xl bg-amber-50 border border-amber-100 p-3 text-center" data-testid="spots-views">
            <p className="text-2xl font-bold text-amber-700">{data.total_views}</p>
            <p className="text-[11px] uppercase tracking-wider text-amber-600/70">Vues cumulées</p>
          </div>
          <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-3 text-center" data-testid="spots-best">
            <p className="text-sm font-bold text-emerald-700 flex items-center justify-center gap-1 mt-1">
              <Trophy size={13} /> {data.best ? data.best.product_name : '—'}
            </p>
            <p className="text-[11px] uppercase tracking-wider text-emerald-600/70 mt-1">
              {data.best ? `Meilleur spot (${data.best.views} vues)` : 'Pas encore de vues'}
            </p>
          </div>
        </div>
        <div className="space-y-2">
          {data.spots.map((s) => (
            <div key={s.product_id} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg"
              data-testid={`spot-row-${s.product_id}`}>
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-medium truncate">{s.product_name}</span>
                {s.languages.map((l) => (
                  <Badge key={l} variant="secondary" className="text-[10px] px-1.5">{LANG_LABELS[l] || l.toUpperCase()}</Badge>
                ))}
              </div>
              <span className="text-xs text-gray-500 inline-flex items-center gap-1 shrink-0">
                <Eye size={12} /> {s.views} vue{s.views > 1 ? 's' : ''}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
