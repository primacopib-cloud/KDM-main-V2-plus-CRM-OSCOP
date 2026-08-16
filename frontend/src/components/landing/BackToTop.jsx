import { useEffect, useState } from 'react';
import { ArrowUp } from 'lucide-react';

export const BackToTop = () => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 900);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <button type="button" aria-label="Retour en haut de page" data-testid="back-to-top-btn"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      className={`fixed bottom-6 right-4 lg:right-20 z-40 w-11 h-11 rounded-full flex items-center justify-center transition-all duration-300 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}`}
      style={{
        background: 'rgba(30,12,52,0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(217,179,90,0.4)',
        boxShadow: '0 10px 30px rgba(0,0,0,0.4)',
      }}>
      <ArrowUp className="w-4.5 h-4.5 text-[#E9CF8E]" size={18} />
    </button>
  );
};
