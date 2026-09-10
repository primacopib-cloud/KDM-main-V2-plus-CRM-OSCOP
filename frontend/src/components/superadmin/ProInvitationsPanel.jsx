import { useEffect, useState } from 'react';
import { Mail, BadgeCheck, Clock, Send, Loader2, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const d10 = (s) => String(s || '').slice(0, 10);
const isExpired = (s) => s && new Date(s) < new Date();

// Invitations pro CommunityPlace (seuil 3 annonces) : stats conversion, code -20 % (expire 30 j), relances auto + manuelle
export const ProInvitationsPanel = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = () => {
    fetch(`${API}/admin/communityplace/pro-invitations`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => toast.error('Erreur de chargement des invitations pro'));
  };
  useEffect(load, []);

  const remind = async (email) => {
    setBusy(email);
    try {
      const r = await fetch(`${API}/admin/communityplace/pro-invitations/remind`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ email }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Erreur');
      toast.success(`Relance envoyée à ${email}`);
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  if (!data) return null;
  const invs = data.invitations || [];
  const stats = data.stats || {};
  return (
    <div className="glass-panel rounded-[22px] p-5 mt-6" data-testid="pro-invitations-panel">
      <h3 className="text-sm font-bold text-white m-0 mb-1 flex items-center gap-2">
        <Mail className="w-4 h-4 text-[#D9B35A]" /> Invitations pro CommunityPlace ({invs.length})
      </h3>
      <p className="text-[11px] text-white/50 m-0 mb-3">
        Participants ayant rejoint 3 annonces payées — invitation -20 % (valable 30 jours), relances J+7 / J+14 et relance manuelle.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4" data-testid="pro-invitations-stats">
        <div className="rounded-xl bg-white/[0.04] border border-white/10 px-3 py-2">
          <p className="text-[9.5px] uppercase tracking-wide text-white/45 m-0">Invitations</p>
          <p className="text-lg font-bold text-white m-0" data-testid="pro-stats-total">{stats.total ?? 0}</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] border border-white/10 px-3 py-2">
          <p className="text-[9.5px] uppercase tracking-wide text-white/45 m-0">Membres convertis</p>
          <p className="text-lg font-bold text-[#8CC63E] m-0" data-testid="pro-stats-converted">{stats.converted ?? 0}</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] border border-white/10 px-3 py-2">
          <p className="text-[9.5px] uppercase tracking-wide text-white/45 m-0 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Taux de conversion</p>
          <p className="text-lg font-bold text-[#E9CF8E] m-0" data-testid="pro-stats-rate">{(stats.conversion_rate ?? 0).toFixed(1).replace('.', ',')} %</p>
        </div>
        <div className="rounded-xl bg-white/[0.04] border border-white/10 px-3 py-2">
          <p className="text-[9.5px] uppercase tracking-wide text-white/45 m-0">Codes -20 % utilisés</p>
          <p className="text-lg font-bold text-white m-0" data-testid="pro-stats-used">{stats.promo_used ?? 0}</p>
        </div>
      </div>
      {!invs.length ? (
        <p className="text-white/40 text-sm m-0" data-testid="pro-invitations-empty">Aucune invitation envoyée pour le moment.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] text-white/80">
            <thead>
              <tr className="text-left text-white/45 uppercase tracking-wide text-[9.5px] border-b border-white/10">
                <th className="py-2 pr-3">Email</th>
                <th className="py-2 pr-3">Invité le</th>
                <th className="py-2 pr-3">Code -20 %</th>
                <th className="py-2 pr-3">Expire le</th>
                <th className="py-2 pr-3">Relances</th>
                <th className="py-2 pr-3">Statut</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {invs.map((i) => (
                <tr key={i.email} className="border-b border-white/[0.06]" data-testid={`pro-invitation-row-${i.email}`}>
                  <td className="py-2 pr-3 font-semibold text-white">
                    {i.email}
                    <span className="block text-[9.5px] text-white/40 font-normal">via {i.reference}</span>
                  </td>
                  <td className="py-2 pr-3">{d10(i.invited_at)}</td>
                  <td className="py-2 pr-3">
                    <span className="font-mono text-[#E9CF8E]">{i.promo_code || '—'}</span>
                    {i.promo_used_at && <span className="ml-1 text-[#8CC63E]">(utilisé)</span>}
                  </td>
                  <td className="py-2 pr-3">
                    {i.promo_expires_at ? (
                      <span className={isExpired(i.promo_expires_at) ? 'text-red-400 font-bold' : ''} data-testid={`pro-invitation-expiry-${i.email}`}>
                        {d10(i.promo_expires_at)}{isExpired(i.promo_expires_at) ? ' (expiré)' : ''}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="py-2 pr-3">
                    <span className="block">J+7 : {i.reminder1_sent_at ? d10(i.reminder1_sent_at) : '—'}</span>
                    <span className="block">J+14 : {i.reminder2_sent_at ? d10(i.reminder2_sent_at) : '—'}</span>
                    {i.manual_reminders > 0 && (
                      <span className="block text-white/40">Manuelle ×{i.manual_reminders} ({d10(i.last_manual_reminder_at)})</span>
                    )}
                  </td>
                  <td className="py-2 pr-3">
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
                  <td className="py-2">
                    {!i.converted && (
                      <button type="button" onClick={() => remind(i.email)} disabled={busy === i.email}
                        data-testid={`pro-invitation-remind-${i.email}`}
                        className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25 transition-colors disabled:opacity-50">
                        {busy === i.email ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                        Relancer maintenant
                      </button>
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
