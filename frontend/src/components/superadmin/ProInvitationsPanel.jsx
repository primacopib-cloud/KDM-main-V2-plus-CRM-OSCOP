import { useEffect, useState } from 'react';
import { Mail, BadgeCheck, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const d10 = (s) => String(s || '').slice(0, 10);

// Invitations pro CommunityPlace (seuil 3 annonces) : email, date, code -20 %, relances, conversion
export const ProInvitationsPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/communityplace/pro-invitations`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => toast.error('Erreur de chargement des invitations pro'));
  }, []);

  if (!data) return null;
  const invs = data.invitations || [];
  return (
    <div className="glass-panel rounded-[22px] p-5 mt-6" data-testid="pro-invitations-panel">
      <h3 className="text-sm font-bold text-white m-0 mb-1 flex items-center gap-2">
        <Mail className="w-4 h-4 text-[#D9B35A]" /> Invitations pro CommunityPlace ({invs.length})
      </h3>
      <p className="text-[11px] text-white/50 m-0 mb-3">
        Participants ayant rejoint 3 annonces payées — invitation -20 % envoyée, relances automatiques J+7 et J+14.
      </p>
      {!invs.length ? (
        <p className="text-white/40 text-sm m-0" data-testid="pro-invitations-empty">Aucune invitation envoyée pour le moment.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] text-white/80">
            <thead>
              <tr className="text-left text-white/45 uppercase tracking-wide text-[9.5px] border-b border-white/10">
                <th className="py-2 pr-3">Email</th>
                <th className="py-2 pr-3">Invité le</th>
                <th className="py-2 pr-3">Annonce déclencheuse</th>
                <th className="py-2 pr-3">Code -20 %</th>
                <th className="py-2 pr-3">Relance J+7</th>
                <th className="py-2 pr-3">Relance J+14</th>
                <th className="py-2">Statut</th>
              </tr>
            </thead>
            <tbody>
              {invs.map((i) => (
                <tr key={i.email} className="border-b border-white/[0.06]" data-testid={`pro-invitation-row-${i.email}`}>
                  <td className="py-2 pr-3 font-semibold text-white">{i.email}</td>
                  <td className="py-2 pr-3">{d10(i.invited_at)}</td>
                  <td className="py-2 pr-3">{i.reference}</td>
                  <td className="py-2 pr-3">
                    <span className="font-mono text-[#E9CF8E]">{i.promo_code || '—'}</span>
                    {i.promo_used_at && <span className="ml-1 text-[#8CC63E]">(utilisé)</span>}
                  </td>
                  <td className="py-2 pr-3">{i.reminder1_sent_at ? d10(i.reminder1_sent_at) : '—'}</td>
                  <td className="py-2 pr-3">{i.reminder2_sent_at ? d10(i.reminder2_sent_at) : '—'}</td>
                  <td className="py-2">
                    {i.converted ? (
                      <span className="inline-flex items-center gap-1 text-[#8CC63E] font-bold" data-testid={`pro-invitation-converted-${i.email}`}>
                        <BadgeCheck className="w-3.5 h-3.5" /> Membre pro
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-orange-300/90" data-testid={`pro-invitation-pending-${i.email}`}>
                        <Clock className="w-3.5 h-3.5" /> Prospect
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
