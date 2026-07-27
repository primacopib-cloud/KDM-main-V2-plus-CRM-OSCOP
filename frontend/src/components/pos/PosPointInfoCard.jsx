import { MapPin, Phone, Mail, Clock3 } from 'lucide-react';

export const PosPointInfoCard = ({ point }) => {
  if (!point) return null;
  return (
    <div className="mb-4 rounded-xl border border-[#D9B35A]/25 bg-[#D9B35A]/[0.04] px-4 py-2.5 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs"
      data-testid="pos-point-info">
      <span className="font-bold text-[#D9B35A]" data-testid="point-info-name">
        {point.name} <span className="text-white/40 font-normal">({point.code})</span>
      </span>
      <span className="flex items-center gap-1 text-white/70" data-testid="point-info-address">
        <MapPin className="w-3 h-3 text-white/40" /> {point.address}, {point.city}
        {point.zone_name ? ` — ${point.zone_name}` : ''}{point.territory ? ` (${point.territory})` : ''}
      </span>
      {point.contact_phone && (
        <span className="flex items-center gap-1 text-white/70 font-mono" data-testid="point-info-phone">
          <Phone className="w-3 h-3 text-white/40" /> {point.contact_phone}
        </span>
      )}
      {point.contact_email && (
        <span className="flex items-center gap-1 text-white/70" data-testid="point-info-email">
          <Mail className="w-3 h-3 text-white/40" /> {point.contact_email}
        </span>
      )}
      {point.opening_hours && (
        <span className="flex items-center gap-1 text-white/70" data-testid="point-info-hours">
          <Clock3 className="w-3 h-3 text-white/40" /> {point.opening_hours}
        </span>
      )}
    </div>
  );
};
