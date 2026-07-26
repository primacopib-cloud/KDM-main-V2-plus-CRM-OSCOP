import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, ArrowRight, Star } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { trackCta } from '../../services/ctaTracking';
import LoloPointsMap from '../LoloPointsMap';
import TerritorySelector from '../TerritorySelector';
import { RelayPodium } from '../RelayPodium';
import { RelayReviewsDialog } from '../pass/RelayReviewsDialog';

/* Section publique : carte du Reseau LOLODRIVE (acquisition / contact) */
export const PublicLolodriveMapSection = () => {
  const [points, setPoints] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [territory, setTerritory] = useState(null);
  const [selected, setSelected] = useState(null);
  const [focusCode, setFocusCode] = useState(() => {
    try { return new URLSearchParams(window.location.search).get('relay'); } catch { return null; }
  });
  const [ratings, setRatings] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [reviewsOpen, setReviewsOpen] = useState(false);

  // Notes moyennes des relais (popups carte)
  useEffect(() => {
    lolodriveAPI.relayReviewStats()
      .then((d) => setRatings(d.stats || {}))
      .catch(() => {});
  }, []);

  // Load territories once on mount
  useEffect(() => {
    lolodriveAPI.listTerritories()
      .then((t) => setTerritories(t.territories || []))
      .catch(() => {});
  }, []);

  // Load points whenever territory changes
  useEffect(() => {
    lolodriveAPI.listLoloPoints({ territory: territory || undefined })
      .then((p) => setPoints(p.points || []))
      .catch(() => setPoints([]));
  }, [territory]);

  // Avis publics du relais sélectionné (fiche modal)
  useEffect(() => {
    if (!selected?.code) { setReviews(null); setReviewsOpen(false); return; }
    lolodriveAPI.relayReviewsList(selected.code)
      .then((d) => setReviews(d.reviews || []))
      .catch(() => setReviews([]));
  }, [selected]);

  // Clic sur un relais du podium → focus carte + ouverture directe des avis
  const viewRelayReviews = (code) => {
    setFocusCode(code);
    const pt = points.find((p) => p.code === code);
    if (pt) setSelected(pt);
    setReviewsOpen(true);
    document.querySelector('[data-testid="lolo-points-map"]')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const activateHere = (point) => {
    // Persist for the registration / PASS purchase funnel
    try {
      localStorage.setItem('kdm_preselected_point', JSON.stringify({
        id: point.id, code: point.code, name: point.name, territory: point.territory,
      }));
      if (point.territory) localStorage.setItem('kdm_territory', point.territory);
    } catch (err) {
      console.debug('Preselection storage failed:', err);
    }
  };

  const selectedRating = selected ? ratings?.[selected.code] : null;

  return (
    <section id="reseau-lolodrive" className="py-10 px-5" data-testid="public-lolodrive-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-5">
          <span className="badge-status mb-3 inline-flex">
            <span className="dot pulse-glow"></span>
            {i18n.t('landing.reseau_lolodrive')}
          </span>
          <h3 className="text-[28px] font-display font-bold tracking-tight mt-2 mb-2">
            {i18n.t('landing.find_relay_prefix')} <span className="text-or-metallise">{i18n.t('landing.le_plus_proche')}</span>
          </h3>
          <p className="text-white/70 text-sm max-w-[60ch] mx-auto">
            <strong>{i18n.t('landing.lolodrive_by_o_scop')}</strong>{i18n.t('landing.lolodrive_desc_mid')}<strong>{i18n.t('landing.cliquez_sur_un_relais')}</strong>{i18n.t('landing.lolodrive_desc_suffix')}
          </p>
        </div>

        <div className="glass-panel rounded-[18px] p-4 mb-3 flex flex-wrap items-center justify-between gap-3">
          <TerritorySelector
            territories={territories}
            value={territory}
            onChange={setTerritory}
            testId="public-territory-selector"
          />
          <div className="text-xs text-white/60 inline-flex items-center gap-1.5" data-testid="public-points-count">
            <MapPin className="w-3.5 h-3.5 text-or-metallise" />
            <strong className="text-white/90">{points.length}</strong> {points.length > 1 ? i18n.t('landing.relay_count_active') : i18n.t('landing.relay_count_active_one')}
          </div>
        </div>

        <LoloPointsMap points={points} territory={territory} focusCode={focusCode} ratings={ratings} height="460px" onSelect={(p) => setSelected(p)} />
        <RelayPodium onView={viewRelayReviews} />

        <div className="mt-3 text-center">
          <Link to="/adhesion-vendeur?type=acheteur_pro">
            <button className="btn-gold inline-flex items-center justify-center gap-2.5 rounded-[14px] px-5 py-3 text-sm font-semibold" data-testid="join-network-btn" onClick={() => trackCta('devenir_relais')}>
              {i18n.t('landing.devenir_relais_lolodrive')}
              <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>

        {/* Avis publics du relais sélectionné */}
        {selected && (
          <RelayReviewsDialog
            open={reviewsOpen}
            onOpenChange={setReviewsOpen}
            pointName={selected.name}
            reviews={reviews || []}
          />
        )}

        {/* Fiche relais — modal coopératif */}
        {selected && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelected(null)}
            data-testid="relay-detail-modal"
          >
            <div
              className="glass-panel rounded-[20px] p-6 max-w-md w-full border border-or-metallise/30"
              onClick={(e) => e.stopPropagation()}
              style={{ background: 'linear-gradient(180deg, rgba(15,16,24,0.95), rgba(7,10,16,0.98))' }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-or-metallise mb-1">{i18n.t('landing.relais_lolodrive')}</div>
                  <h3 className="text-2xl font-display font-bold leading-tight">{selected.name}</h3>
                  <div className="font-mono text-xs text-white/40 mt-1">{selected.code} · {selected.territory}</div>
                </div>
                <button onClick={() => setSelected(null)} className="text-white/40 hover:text-white text-xl leading-none px-2" data-testid="close-relay-detail">×</button>
              </div>
              <div className="separator-premium"><span className="dot"></span></div>
              {selected.photo_url && (
                <img src={selected.photo_url} alt={selected.name} data-testid="relay-detail-photo"
                  className="w-full h-36 object-cover rounded-xl border border-[#D9B35A]/30 mb-4" />
              )}
              <div className="space-y-2 text-sm mb-5">
                <div className="flex items-start gap-2"><MapPin className="w-4 h-4 mt-0.5 text-violet-premium flex-shrink-0" /><span>{selected.address || '—'}, {selected.city || '—'}</span></div>
                {selected.zone_name && <div className="text-xs text-white/50 ml-6">{i18n.t('landing.zone_label')} {selected.zone_name}</div>}
                {selectedRating && (
                  <button
                    type="button"
                    onClick={() => setReviewsOpen(true)}
                    data-testid="relay-detail-reviews-btn"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#E9CF8E] px-2.5 py-1.5 rounded-lg border border-[#D9B35A]/35 bg-[#D9B35A]/[0.08] hover:bg-[#D9B35A]/[0.16] transition-colors"
                  >
                    <Star className="w-3.5 h-3.5 fill-[#D9B35A] text-[#D9B35A]" />
                    {selectedRating.avg} · Voir les {selectedRating.count} avis
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 mb-5 text-center">
                <div className="rounded-lg bg-vert-lime/10 border border-vert-lime/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-vert-lime mb-0.5">{i18n.t('landing.drive')}</div>
                  <div className="text-xs text-white/80">{i18n.t('landing.retrait_cooperatif')}</div>
                </div>
                <div className="rounded-lg bg-violet-premium/10 border border-violet-premium/30 p-3">
                  <div className="text-[10px] uppercase tracking-wider text-violet-premium mb-0.5">{i18n.t('landing.livraison')}</div>
                  <div className="text-xs text-white/80">{i18n.t('landing.livraison_locale')}</div>
                </div>
              </div>
              <Link to="/pass-lolodrive/inscription" onClick={() => activateHere(selected)} data-testid="activate-pass-here-btn">
                <button className="btn-gold w-full inline-flex items-center justify-center gap-2 rounded-[14px] py-3 text-sm font-semibold">
                  {i18n.t('landing.activer_mon_pass_ici')}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </Link>
              <p className="text-[11px] text-white/40 mt-3 text-center">
                {i18n.t('landing.vous_serez_redirige_vers')}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
