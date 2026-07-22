import React from 'react';
import { useLocation } from 'react-router-dom';

const HIDDEN_PREFIXES = ['/admin', '/superadmin', '/pos', '/crm', '/reporting'];
const WA_NUMBER = '590690906429';
const WA_TEXT = encodeURIComponent("Bonjour, j'ai besoin d'aide (S.A.V / support client) sur la Communityplace KDMARCHÉ × O'SCOP.");

export const WhatsAppSupport = () => {
  const { pathname } = useLocation();
  if (HIDDEN_PREFIXES.some((p) => pathname.startsWith(p))) return null;
  return (
    <a
      href={`https://wa.me/${WA_NUMBER}?text=${WA_TEXT}`}
      target="_blank"
      rel="noreferrer"
      data-testid="whatsapp-support-btn"
      title="Support client S.A.V — WhatsApp"
      aria-label="Support client WhatsApp"
      className="fixed bottom-5 left-5 z-[60] w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110"
      style={{ background: '#25D366' }}
    >
      <svg viewBox="0 0 32 32" width="26" height="26" fill="#fff" aria-hidden="true">
        <path d="M16.04 4.5c-6.35 0-11.5 5.09-11.5 11.37 0 2.01.54 3.96 1.56 5.68L4.5 27.5l6.13-1.58a11.63 11.63 0 0 0 5.41 1.33c6.35 0 11.5-5.1 11.5-11.38S22.39 4.5 16.04 4.5Zm0 20.8c-1.73 0-3.42-.46-4.9-1.32l-.35-.2-3.64.94.97-3.5-.23-.36a9.3 9.3 0 0 1-1.45-4.99c0-5.17 4.26-9.38 9.6-9.38 5.33 0 9.59 4.2 9.59 9.38 0 5.18-4.26 9.42-9.59 9.42Zm5.27-7.04c-.29-.14-1.7-.83-1.97-.93-.26-.1-.46-.14-.65.14-.19.29-.74.93-.9 1.12-.17.19-.34.21-.62.07-.29-.14-1.22-.44-2.31-1.42-.86-.75-1.43-1.68-1.6-1.96-.17-.29-.02-.44.12-.58.13-.13.29-.34.43-.5.14-.17.19-.29.29-.48.1-.2.05-.36-.02-.5-.07-.15-.65-1.54-.9-2.11-.23-.55-.47-.48-.65-.49h-.55c-.19 0-.5.07-.77.36-.26.28-1 .96-1 2.35 0 1.39 1.03 2.73 1.17 2.92.14.19 2.03 3.04 4.91 4.27.69.29 1.22.46 1.64.6.69.21 1.31.18 1.8.11.55-.08 1.7-.68 1.94-1.34.24-.66.24-1.22.17-1.34-.07-.12-.26-.19-.55-.33Z"/>
      </svg>
    </a>
  );
};
