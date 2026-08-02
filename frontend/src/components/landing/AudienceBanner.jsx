export const AudienceBanner = ({ id, icon: Icon, kicker, title, subtitle, color = '#D9B35A', testId }) => (
  <section id={id} className="max-w-[1160px] mx-auto px-5 pt-4 mb-10 scroll-mt-24" data-testid={testId}>
    <div
      className="rounded-[22px] px-6 py-6 flex items-center gap-4"
      style={{
        background: `linear-gradient(135deg, ${color}1f, rgba(255,255,255,0.02))`,
        border: `1px solid ${color}55`,
      }}
    >
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${color}22`, border: `1px solid ${color}66` }}
      >
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] m-0 font-bold" style={{ color }}>{kicker}</p>
        <h2 className="font-display text-2xl md:text-3xl m-0 mt-1 text-white">{title}</h2>
        <p className="text-white/60 text-sm m-0 mt-1">{subtitle}</p>
      </div>
    </div>
  </section>
);
