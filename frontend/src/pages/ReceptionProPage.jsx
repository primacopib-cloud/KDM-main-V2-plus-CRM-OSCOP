import Seo from '../components/Seo';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Lock, PackageCheck, ShieldCheck, CreditCard, Timer } from 'lucide-react';
import { API } from '../services/http';

// Page « Règlement à Réception Pro » : gate réservé aux acheteurs pro, redirection vers l'espace si membre
export default function ReceptionProPage() {
  const [pro, setPro] = useState(null);
  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; } })();

  useEffect(() => {
    if (!user?.email) { setPro(false); return; }
    fetch(`${API}/public/purchase-needs/join/status?email=${encodeURIComponent(user.email)}`)
      .then((r) => (r.ok ? r.json() : { pro: false }))
      .then((d) => setPro(Boolean(d.pro)))
      .catch(() => setPro(false));
  }, [user?.email]);

  if (pro === true) return <Navigate to="/espace-acheteur" replace />;

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2a0c4a 0%, #1F0A33 100%)' }}>
      <Seo title="Règlement à Réception Pro — Accès réservé" description="Le règlement à réception est réservé aux acheteurs professionnels adhérents de la centrale KDMARCHÉ × O'SCOP." />
      <NavBar />
      <main className="max-w-[680px] mx-auto px-5 pt-28 pb-16" data-testid="reception-pro-page">
        <div className="glass-panel-soft rounded-[22px] p-8 text-center" data-testid="reception-pro-gate">
          <Lock className="w-8 h-8 text-[#D9B35A] mx-auto mb-3" />
          <h1 className="text-lg font-bold text-white mb-2">Accès réservé aux acheteurs professionnels</h1>
          <p className="text-white/70 text-sm mb-4">
            Le service <b className="text-[#E9CF8E]">Règlement à Réception Pro</b> — commandez sans acompte,
            réglez après validation électronique de la livraison — est accessible exclusivement aux acheteurs
            professionnels disposant d'une adhésion active à la centrale O'SCOP.
          </p>
          <div className="text-left rounded-xl border border-white/12 bg-white/[0.04] p-4 mb-5" data-testid="reception-pro-presentation">
            <p className="text-[13px] font-bold text-[#E9CF8E] m-0 mb-2">
              <PackageCheck className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
              Règlement à réception, le paiement coopératif sécurisé
            </p>
            <ul className="m-0 pl-4 space-y-1 text-[12.5px] text-white/70">
              <li>Aucun acompte ni paiement de la marchandise avant réception</li>
              <li>Règlement déclenché après validation électronique de la livraison LOGI'SCOP</li>
              <li>Plafond d'encours accordé par KDMARCHÉ selon votre profil</li>
              <li>Disponible sur les marchandises éligibles, tous territoires desservis</li>
            </ul>
            <p className="text-[12px] text-white/50 m-0 mt-2">
              Adhérez à la centrale pour débloquer le règlement à réception et vérifier votre éligibilité.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <a href="/connexion?redirect=/reglement-reception" data-testid="reception-pro-gate-login"
              className="on-gold inline-flex items-center gap-1.5 px-4 py-2.5 rounded-[12px] bg-[#D9B35A] hover:bg-[#F2D07A] text-sm font-bold">
              <ShieldCheck className="w-4 h-4" /> Se connecter
            </a>
            <a href="/adhesion-vendeur?type=acheteur_pro" data-testid="reception-pro-gate-join"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-[12px] border border-[#8CC63E]/50 text-[#B6E27A] hover:bg-[#8CC63E]/10 text-sm font-bold">
              <CreditCard className="w-4 h-4" /> Adhérer à la centrale
            </a>
          </div>
          {pro === null && (
            <p className="text-[11px] text-white/40 mt-4 inline-flex items-center gap-1.5" data-testid="reception-pro-checking">
              <Timer className="w-3 h-3 animate-pulse" /> Vérification de votre statut membre…
            </p>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
