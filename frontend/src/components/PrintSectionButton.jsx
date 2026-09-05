import { Printer } from 'lucide-react';

export const PrintSectionButton = ({ label = 'Imprimer cette section' }) => {
  const handlePrint = (e) => {
    const section = e.currentTarget.closest('[data-print-section]');
    if (!section) { window.print(); return; }
    document.body.classList.add('print-focus');
    section.classList.add('print-target');
    const cleanup = () => {
      document.body.classList.remove('print-focus');
      section.classList.remove('print-target');
      window.removeEventListener('afterprint', cleanup);
    };
    window.addEventListener('afterprint', cleanup);
    window.print();
    setTimeout(cleanup, 2000);
  };
  return (
    <button
      type="button"
      onClick={handlePrint}
      title={label}
      data-testid="print-section-btn"
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border border-white/15 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
    >
      <Printer className="w-3.5 h-3.5" /> Imprimer
    </button>
  );
};
