import React, { useEffect, useState } from 'react';
import { Star, Quote, BadgeCheck } from 'lucide-react';
import i18n from '@/i18n';

const VERIFIED_LABELS = { fr: 'Membre coopérateur vérifié', en: 'Verified cooperative member', es: 'Miembro cooperador verificado' };

export const TestimonialsSection = () => {
  const [items, setItems] = useState([]);
  const lang = (i18n.language || 'fr').slice(0, 2);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/testimonials?lang=${lang}`)
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, [lang]);

  if (!items.length) return null;
  return (
    <section id="temoignages" className="py-10 px-5" data-testid="testimonials-section">
      <div className="max-w-[1160px] mx-auto">
        <div className="text-center mb-8">
          <h3 className="text-[28px] font-display font-bold tracking-tight mb-2">
            Ils font vivre la <span className="text-[#D9B35A]">Communityplace</span>
          </h3>
          <p className="text-white/70 text-sm max-w-[60ch] mx-auto">
            Témoignages de vendeurs et d'acheteurs professionnels membres de la coopérative.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {items.slice(0, 6).map((t) => (
            <div key={t.id} data-testid={`public-testimonial-${t.id}`}
              className="rounded-[18px] p-5 bg-white/[0.05] border border-white/10 backdrop-blur-sm flex flex-col">
              <Quote size={20} className="text-[#D9B35A] mb-3" />
              <p className="text-sm text-white/80 italic flex-1">« {t.text} »</p>
              <div className="mt-4 pt-3 border-t border-white/10">
                <div className="flex items-center gap-1 text-[#E9CF8E] mb-1">
                  {Array.from({ length: t.rating || 5 }).map((_, i) => <Star key={i} size={12} fill="currentColor" />)}
                </div>
                <p className="text-sm text-white font-semibold flex items-center gap-1.5">
                  {t.name}
                  {t.verified_member && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-400/15 text-emerald-300 text-[10px] font-medium"
                      data-testid={`verified-badge-${t.id}`}>
                      <BadgeCheck size={11} /> {VERIFIED_LABELS[lang] || VERIFIED_LABELS.fr}
                    </span>
                  )}
                </p>
                <p className="text-xs text-white/50">
                  {[t.role, t.company, t.territory].filter(Boolean).join(' · ')}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
