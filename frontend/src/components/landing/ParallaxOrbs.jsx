import { useEffect, useRef } from 'react';

const ORBS = [
  { top: '4%', left: '-6%', size: 360, color: 'rgba(217,179,90,0.18)', speed: 0.14 },
  { top: '18%', right: '-8%', size: 460, color: 'rgba(91,46,140,0.4)', speed: -0.1 },
  { top: '42%', left: '4%', size: 300, color: 'rgba(140,198,62,0.14)', speed: 0.07 },
  { top: '60%', right: '6%', size: 340, color: 'rgba(245,166,35,0.13)', speed: -0.16 },
  { top: '82%', left: '20%', size: 380, color: 'rgba(217,179,90,0.12)', speed: 0.1 },
];

export const ParallaxOrbs = () => {
  const ref = useRef(null);

  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const y = window.scrollY;
        if (!ref.current) return;
        Array.from(ref.current.children).forEach((c, i) => {
          c.style.transform = `translate3d(0, ${Math.round(y * ORBS[i].speed)}px, 0)`;
        });
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(raf); };
  }, []);

  return (
    <div ref={ref} aria-hidden="true" data-testid="parallax-orbs"
      className="absolute inset-0 pointer-events-none" style={{ zIndex: -1 }}>
      {ORBS.map((o, i) => (
        <div key={i} className="parallax-orb"
          style={{ top: o.top, left: o.left, right: o.right, width: o.size, height: o.size, background: o.color }} />
      ))}
    </div>
  );
};
