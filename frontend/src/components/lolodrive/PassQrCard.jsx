import { QRCodeSVG } from 'qrcode.react';

// QR-code du PASS : scanné en caisse par l'opérateur pour retrouver le client instantanément
export const PassQrCard = ({ passId }) => {
  if (!passId) return null;
  return (
    <div className="flex flex-col items-center gap-2 p-3 rounded-2xl bg-white border border-[#D9B35A]/50 shadow-lg" data-testid="pass-qr-card">
      <QRCodeSVG value={passId} size={116} level="M" fgColor="#111111" bgColor="#ffffff" />
      <p className="text-[10px] font-bold text-black/70 uppercase tracking-wider">Mon QR PASS</p>
      <p className="text-[9px] text-black/40 font-mono -mt-1.5">{passId}</p>
    </div>
  );
};
