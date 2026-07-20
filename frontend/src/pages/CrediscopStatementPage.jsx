import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Coins, Download, Ticket, Wallet, Building2 } from 'lucide-react';
import { BrandLogos } from '../components/BrandLogos';

const API = process.env.REACT_APP_BACKEND_URL;
const KIND_META = {
  vendor: { label: 'Crédits IA & spots vidéo', icon: Coins },
  consultations: { label: "CREDI'SCOP consultations", icon: Ticket },
  org: { label: 'Wallet organisation', icon: Building2 },
  user: { label: 'Crédits personnels', icon: Wallet },
};
const SRC_LABEL = { vendor: 'IA', consultations: 'Consult.', org: 'Org', user: 'Perso' };

export default function CrediscopStatementPage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/me/crediscop/statement`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen" style={{ background: '#1F0A33' }} data-testid="crediscop-statement-page">
      <header className="border-b border-white/10 px-5 py-3">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <BrandLogos size="sm" />
          <h1 className="text-base font-bold text-white flex-1">Mon relevé CREDI'SCOP unifié</h1>
          <a href={`${API}/api/me/crediscop/statement.pdf`} target="_blank" rel="noreferrer" data-testid="statement-pdf-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
            style={{ background: '#D9B35A', color: '#1F0A33' }}>
            <Download className="w-3.5 h-3.5" /> Relevé PDF
          </a>
          <Link to="/espace-vendeur" className="inline-flex items-center gap-1 text-xs text-white/60 hover:text-white" data-testid="statement-back-link">
            <ArrowLeft className="w-3.5 h-3.5" /> Retour
          </Link>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-5 py-6 space-y-5">
        {!data && <p className="text-sm text-white/40">Chargement du relevé…</p>}
        {data && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {(data.balances || []).map((b) => {
                const meta = KIND_META[b.kind] || KIND_META.user;
                const Icon = meta.icon;
                return (
                  <div key={b.kind} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4" data-testid={`statement-balance-${b.kind}`}>
                    <p className="text-xs text-white/55 flex items-center gap-1.5"><Icon className="w-3.5 h-3.5 text-[#D9B35A]" /> {meta.label}</p>
                    <p className="text-2xl font-bold text-white mt-1">{b.balance} <span className="text-xs font-semibold text-[#E9CF8E]">CREDI'SCOP</span></p>
                  </div>
                );
              })}
            </div>
            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Mouvements récents (tous registres)</h2>
              {!(data.entries || []).length && <p className="text-sm text-white/40">Aucun mouvement.</p>}
              <div className="space-y-1">
                {(data.entries || []).slice(0, 80).map((e, i) => (
                  <div key={i} className="flex items-center gap-3 text-[13px] py-1.5 border-b border-white/5 last:border-0">
                    <span className={`font-bold w-14 text-right ${e.amount > 0 ? 'text-emerald-400' : 'text-red-400'}`}>{e.amount > 0 ? '+' : ''}{e.amount}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/50 w-16 text-center">{SRC_LABEL[e.source] || e.source}</span>
                    <span className="flex-1 text-white/75 truncate">{e.label}</span>
                    <span className="text-xs text-white/40 whitespace-nowrap">{String(e.at || '').slice(0, 16).replace('T', ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-white/40">
              Relevé unifié : crédits IA/spots vidéo, CREDI'SCOP consultations, wallets. Chaque registre reste juridiquement
              distinct — aucune conversion entre registres, aucun usage pour les marchandises, la RCR ou FOGEDOM-SCIC.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
