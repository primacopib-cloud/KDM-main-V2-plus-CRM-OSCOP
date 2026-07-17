import i18n from '@/i18n';
import { X, FileText } from 'lucide-react';

const eur = (n) => (n ?? 0).toLocaleString(i18n.language, { style: 'currency', currency: 'EUR' });

export const IaboisQuoteModal = ({ quote, onClose }) => {
  if (!quote) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      data-testid="iabois-quote-modal"
    >
      <div
        className="glass-panel rounded-[20px] p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        style={{ background: '#FFFFFF', boxShadow: '0 24px 64px rgba(76,42,110,0.25)' }}
      >
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-display text-xl flex items-center gap-2" style={{ color: 'var(--kdm-bleu-logistique)' }}>
            <FileText size={18} style={{ color: '#D9B35A' }} />
            {i18n.t('adm.quote_title')}
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ color: '#B8860B', background: '#D9B35A22' }}>
              {i18n.t('adm.quote_draft')}
            </span>
          </h3>
          <button type="button" onClick={onClose} data-testid="iabois-quote-close" className="opacity-50 hover:opacity-100 p-1">
            <X size={18} />
          </button>
        </div>
        <p className="text-sm font-medium mb-0.5" data-testid="iabois-quote-project-title">{quote.title}</p>
        <p className="text-xs opacity-60 mb-4">{i18n.t('adm.quote_client')} : {quote.client || '—'}</p>

        <table className="w-full text-sm mb-4">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider opacity-50 text-left border-b border-black/10">
              <th className="py-2 pr-2">{i18n.t('adm.quote_line')}</th>
              <th className="py-2 pr-2 text-right">{i18n.t('adm.quote_qty')}</th>
              <th className="py-2 pr-2 text-right">{i18n.t('adm.quote_unit_price')}</th>
              <th className="py-2 text-right">{i18n.t('adm.quote_total')}</th>
            </tr>
          </thead>
          <tbody>
            {(quote.lines || []).map((l) => (
              <tr key={l.label} className="border-b border-black/5">
                <td className="py-2 pr-2">{l.label}</td>
                <td className="py-2 pr-2 text-right whitespace-nowrap">{l.qty} {l.unit}</td>
                <td className="py-2 pr-2 text-right">{eur(l.unit_price_ht)}</td>
                <td className="py-2 text-right font-medium">{eur(l.total_ht)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex flex-col items-end gap-1 text-sm" data-testid="iabois-quote-totals">
          <div className="flex gap-6"><span className="opacity-60">{i18n.t('adm.quote_total_ht')}</span><strong>{eur(quote.total_ht)}</strong></div>
          <div className="flex gap-6"><span className="opacity-60">{i18n.t('adm.quote_tva', { rate: quote.tva_rate })}</span><span>{eur(quote.total_tva)}</span></div>
          <div className="flex gap-6 text-base"><span className="opacity-70">{i18n.t('adm.quote_total_ttc')}</span><strong style={{ color: '#B8860B' }}>{eur(quote.total_ttc)}</strong></div>
        </div>

        <p className="text-[11px] opacity-50 mt-4">{i18n.t('adm.quote_prefill_note')}</p>
      </div>
    </div>
  );
};
