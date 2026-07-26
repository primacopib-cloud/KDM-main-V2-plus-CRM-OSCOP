import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Phone, Mail, Clock, Truck, Car, Navigation, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

export const PassRelayHeader = () => {
  const [point, setPoint] = useState(null);
  const [noRelay, setNoRelay] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);

  useEffect(() => {
    let pre = null;
    try { pre = JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null'); } catch { /* ignore */ }
    if (!pre?.code) { setNoRelay(true); return; }
    lolodriveAPI.listLoloPoints()
      .then((d) => setPoint((d.points || []).find((p) => p.code === pre.code) || pre))
      .catch(() => setPoint(pre));
  }, []);

  if (noRelay) {
    return (
      <div className="mb-6 flex items-center gap-3 rounded-2xl border border-[#D9B35A]/25 bg-white/[0.03] px-4 py-3" data-testid="pass-relay-header-empty">
        <img src="/lolodrive-logo.jpg" alt="" className="w-9 h-9 rounded-full bg-white object-contain" />
        <p className="text-sm text-white/60 flex-1">Aucun relais LOLODRIVE sélectionné pour vos retraits.</p>
        <Link to="/#reseau-lolodrive" data-testid="pass-relay-choose-link"
          className="text-xs font-bold px-3 py-1.5 rounded-full" style={{ background: '#D9B35A', color: '#1F0A33' }}>
          Choisir mon relais
        </Link>
      </div>
    );
  }
  if (!point) return null;

  return (
    <div className="mb-6 rounded-2xl border border-[#D9B35A]/30 p-4 sm:p-5"
      style={{ background: 'linear-gradient(90deg, rgba(217,179,90,0.09), rgba(124,58,237,0.08))' }}
      data-testid="pass-relay-header">
      <div className="flex flex-wrap items-start gap-4">
        <img src="/lolodrive-logo.jpg" alt="LOLODRIVE"
          className="w-12 h-12 rounded-xl bg-white object-contain p-0.5 border border-[#D9B35A]/50 shrink-0" />
        <div className="min-w-[180px]">
          <p className="text-[10px] uppercase tracking-[0.18em] text-[#D9B35A] font-bold">Mon relais LOLODRIVE</p>
          <p className="text-base font-bold text-white" data-testid="pass-relay-name">{point.name}</p>
          <p className="text-[11px] text-white/40 font-mono flex items-center gap-1.5">
            {point.code}{point.territory ? ` · ${point.territory}` : ''}
            <Link to="/#reseau-lolodrive" data-testid="pass-relay-map-link"
              title="Voir sur la carte des relais LOLODRIVE"
              className="text-[#D9B35A] hover:text-[#E9CF8E] transition-transform hover:scale-125">
              <MapPin className="w-3.5 h-3.5" />
            </Link>
          </p>
        </div>
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 text-xs text-white/75 min-w-[240px]">
          {(point.address || point.city) && (
            <span className="flex items-center gap-1.5" data-testid="pass-relay-address">
              <MapPin className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" />
              {[point.address, point.city].filter(Boolean).join(', ')}
            </span>
          )}
          {point.contact_phone && (
            <a href={`tel:${point.contact_phone}`} className="flex items-center gap-1.5 hover:text-white" data-testid="pass-relay-phone">
              <Phone className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" /> {point.contact_phone}
            </a>
          )}
          {point.contact_email && (
            <a href={`mailto:${point.contact_email}`} className="flex items-center gap-1.5 hover:text-white" data-testid="pass-relay-email">
              <Mail className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" /> {point.contact_email}
            </a>
          )}
          {point.opening_hours && (
            <span className="flex items-center gap-1.5" data-testid="pass-relay-hours">
              <Clock className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" /> {point.opening_hours}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <a
            href={point.lat && point.lng
              ? `https://www.google.com/maps/dir/?api=1&destination=${point.lat},${point.lng}`
              : `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent([point.name, point.address, point.city].filter(Boolean).join(', '))}`}
            target="_blank" rel="noreferrer" data-testid="pass-relay-directions-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold text-black transition-transform hover:scale-105"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #c9a34a)' }}>
            <Navigation className="w-3.5 h-3.5" /> Y aller
          </a>
          <div className="flex gap-1.5">
            {point.offers_drive && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase text-emerald-300 border border-emerald-400/40 bg-emerald-500/10" data-testid="pass-relay-drive-badge">
                <Car className="w-3 h-3" /> Drive
              </span>
            )}
            {point.offers_delivery && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase text-sky-300 border border-sky-400/40 bg-sky-500/10" data-testid="pass-relay-delivery-badge">
                <Truck className="w-3 h-3" /> Livraison
              </span>
            )}
          </div>
          <button type="button" onClick={() => setDeliveryOpen(true)} data-testid="pass-relay-delivery-btn"
            className="text-[11px] text-white/60 hover:text-[#D9B35A] inline-flex items-center gap-1 transition-colors">
            <Truck className="w-3.5 h-3.5" /> Livraison
          </button>
        </div>
      </div>

      <Dialog open={deliveryOpen} onOpenChange={setDeliveryOpen}>
        <DialogContent className="bg-[#1A092D] border-white/15 text-white max-w-md" data-testid="pass-relay-delivery-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <img src="/lolodrive-logo.jpg" alt="" className="w-7 h-7 rounded-lg bg-white object-contain" />
              Livraison — {point.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-2 p-3 rounded-xl bg-white/[0.04] border border-white/10">
              <Clock className="w-4 h-4 text-[#D9B35A] shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Horaires d'ouverture</p>
                <p data-testid="delivery-dialog-hours">{point.opening_hours || 'Horaires non renseignés — contactez le relais.'}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {point.offers_drive && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase text-emerald-300 border border-emerald-400/40 bg-emerald-500/10">
                  <Car className="w-3.5 h-3.5" /> Drive
                </span>
              )}
              {point.offers_delivery ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase text-sky-300 border border-sky-400/40 bg-sky-500/10">
                  <Truck className="w-3.5 h-3.5" /> Livraison proposée
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase text-white/40 border border-white/15 bg-white/5">
                  <Truck className="w-3.5 h-3.5" /> Livraison non proposée
                </span>
              )}
            </div>
            <div className="flex items-start gap-2 p-3 rounded-xl bg-[#D9B35A]/[0.07] border border-[#D9B35A]/25">
              <Info className="w-4 h-4 text-[#D9B35A] shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] uppercase tracking-wider text-[#D9B35A] font-bold">Conditions de livraison</p>
                <p className="text-white/80" data-testid="delivery-dialog-conditions">
                  {point.delivery_conditions
                    || (point.offers_delivery
                      ? 'Conditions non renseignées — contactez le relais pour les modalités.'
                      : 'Ce relais ne propose pas la livraison à domicile : retrait sur place ou Drive uniquement.')}
                </p>
              </div>
            </div>
            {point.contact_phone && (
              <a href={`tel:${point.contact_phone}`} className="flex items-center gap-2 text-xs text-white/60 hover:text-white">
                <Phone className="w-3.5 h-3.5 text-[#D9B35A]" /> {point.contact_phone}
              </a>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};