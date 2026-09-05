import { useState } from 'react';
import { Printer, FileDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { downloadSectionPdf } from '../utils/sectionPdf';

const btnCls = 'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border border-white/15 text-white/70 hover:text-white hover:bg-white/10 transition-colors';

export const PrintSectionButton = ({ label = 'Imprimer cette section' }) => {
  const [pdfLoading, setPdfLoading] = useState(false);

  const getSection = (e) => e.currentTarget.closest('[data-print-section]');

  const handlePrint = (e) => {
    const section = getSection(e);
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

  const handlePdf = async (e) => {
    const section = getSection(e);
    if (!section || pdfLoading) return;
    setPdfLoading(true);
    try {
      const title = section.querySelector('h2, h3')?.textContent?.trim() || 'section';
      await downloadSectionPdf(section, title);
      toast.success('PDF téléchargé');
    } catch {
      toast.error('Échec de la génération du PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-1.5">
      <button type="button" onClick={handlePrint} title={label} data-testid="print-section-btn" className={btnCls}>
        <Printer className="w-3.5 h-3.5" /> Imprimer
      </button>
      <button type="button" onClick={handlePdf} disabled={pdfLoading} title="Télécharger cette section en PDF" data-testid="pdf-section-btn" className={btnCls}>
        {pdfLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />} PDF
      </button>
    </span>
  );
};
