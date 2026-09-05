import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';

const PDF_STYLE = `
.pdf-clone-root, .pdf-clone-root * {
  background: #FFFFFF !important; background-image: none !important;
  color: #000 !important; border-color: #999 !important;
  box-shadow: none !important; text-shadow: none !important;
}
.pdf-clone-root button, .pdf-clone-root select, .pdf-clone-root input[type="checkbox"] { display: none !important; }
.pdf-clone-root th, .pdf-clone-root td { border: 1px solid #444 !important; padding: 4px 8px !important; }
.pdf-clone-root thead th { background: #EEE !important; font-weight: 700; }
.pdf-clone-root svg { color: #000 !important; }
`;

const loadLogoPng = (src) => new Promise((resolve, reject) => {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => {
    const c = document.createElement('canvas');
    c.width = img.width; c.height = img.height;
    c.getContext('2d').drawImage(img, 0, 0);
    resolve(c.toDataURL('image/png'));
  };
  img.onerror = reject;
  img.src = src;
});

export async function downloadSectionPdf(section, title = 'section') {
  const canvas = await html2canvas(section, {
    scale: 2,
    backgroundColor: '#FFFFFF',
    useCORS: true,
    onclone: (doc, cloned) => {
      cloned.classList.add('pdf-clone-root');
      const st = doc.createElement('style');
      st.textContent = PDF_STYLE;
      doc.head.appendChild(st);
    },
  });
  const pdf = new jsPDF('p', 'mm', 'a4');
  const pw = 210, ph = 297, margin = 10, headerH = 22, footerH = 12;
  const contentW = pw - margin * 2;
  const contentH = ph - headerH - footerH - margin;
  const pxPerMm = canvas.width / contentW;
  const pagePx = Math.floor(contentH * pxPerMm);
  const nPages = Math.max(1, Math.ceil(canvas.height / pagePx));

  let logo = null;
  try { logo = await loadLogoPng('/logos/oscop.webp'); } catch { /* sans logo */ }
  const now = new Date();
  const dateStr = `Imprimé le ${now.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} à ${now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;

  for (let i = 0; i < nPages; i++) {
    if (i > 0) pdf.addPage();
    const slice = document.createElement('canvas');
    slice.width = canvas.width;
    slice.height = Math.min(pagePx, canvas.height - i * pagePx);
    const ctx = slice.getContext('2d');
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, slice.width, slice.height);
    ctx.drawImage(canvas, 0, i * pagePx, canvas.width, slice.height, 0, 0, canvas.width, slice.height);

    if (logo) pdf.addImage(logo, 'PNG', margin, 6, 12, 12);
    pdf.setFontSize(11); pdf.setFont(undefined, 'bold'); pdf.setTextColor(0);
    pdf.text("SCIC SAS OBJECTIF SCOP OUTREMER — Super Admin", margin + 15, 11);
    pdf.setFontSize(8); pdf.setFont(undefined, 'normal'); pdf.setTextColor(70);
    pdf.text(dateStr, margin + 15, 16);
    pdf.setDrawColor(0);
    pdf.line(margin, headerH - 2, pw - margin, headerH - 2);

    pdf.addImage(slice.toDataURL('image/jpeg', 0.92), 'JPEG', margin, headerH + 2, contentW, slice.height / pxPerMm);

    pdf.line(margin, ph - footerH + 2, pw - margin, ph - footerH + 2);
    pdf.setFontSize(7.5); pdf.setTextColor(80);
    pdf.text('Document confidentiel — SCIC SAS OBJECTIF SCOP OUTREMER — Diffusion interne uniquement', pw / 2, ph - 6, { align: 'center' });
    pdf.text(`Page ${i + 1} / ${nPages}`, pw - margin, ph - 6, { align: 'right' });
  }
  const slug = title.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section';
  pdf.save(`${slug}-${now.toISOString().slice(0, 10)}.pdf`);
}
