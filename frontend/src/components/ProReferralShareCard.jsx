import { useEffect, useState } from 'react';
import { Gift, Copy, Users } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../services/http';

// Carte de parrainage membre pro : lien -20 % à partager avec ses contacts
export const ProReferralShareCard = () => {
  const [ref, setRef] = useState(null);

  useEffect(() => {
    fetch(`${API}/pro-referral/my-code`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setRef)
      .catch(() => {});
  }, []);

  if (!ref) return null;
  const waText = `🎁 Rejoignez la coopérative KDMARCHÉ × O'SCOP avec -${ref.percent} % sur votre première adhésion professionnelle grâce à mon lien : ${ref.share_url}`;
  return (
    <div className="glass-panel rounded-[22px] p-5 mt-6 border border-[#D9B35A]/25" data-testid="pro-referral-card">
      <h3 className="text-sm font-bold text-white m-0 mb-1 flex items-center gap-2">
        <Gift className="w-4 h-4 text-[#D9B35A]" /> Parrainez vos contacts — offrez-leur -{ref.percent} %
      </h3>
      <p className="text-[11px] text-white/55 m-0 mb-3">
        Partagez votre lien : vos contacts bénéficient de <b className="text-[#E9CF8E]">-{ref.percent} % sur leur première adhésion professionnelle</b>.
        {ref.uses > 0 && (
          <span className="ml-1 inline-flex items-center gap-1 text-[#8CC63E]" data-testid="pro-referral-uses">
            <Users className="w-3 h-3" /> {ref.uses} adhésion{ref.uses > 1 ? 's' : ''} grâce à vous
          </span>
        )}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <code className="text-[11px] font-mono px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-[#E9CF8E] truncate max-w-full"
          data-testid="pro-referral-link">{ref.share_url}</code>
        <button type="button" data-testid="pro-referral-copy"
          onClick={() => navigator.clipboard.writeText(ref.share_url)
            .then(() => toast.success('Lien de parrainage copié !'))
            .catch(() => toast.error('Copie impossible'))}
          className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-2 rounded-lg bg-[#D9B35A] text-[#1F0A33] hover:brightness-110 transition-[filter]">
          <Copy className="w-3.5 h-3.5" /> Copier le lien
        </button>
        <a data-testid="pro-referral-whatsapp"
          href={`https://wa.me/?text=${encodeURIComponent(waText)}`} target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-2 rounded-lg bg-[#25D366]/20 text-[#4be284] border border-[#25D366]/40 hover:bg-[#25D366]/30 transition-colors">
          <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.52.149-.174.198-.298.297-.497.1-.198.05-.371-.025-.52-.074-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          WhatsApp
        </a>
      </div>
    </div>
  );
};
