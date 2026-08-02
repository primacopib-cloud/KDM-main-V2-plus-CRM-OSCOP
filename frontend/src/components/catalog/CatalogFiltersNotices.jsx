import i18n from '@/i18n';
import { AlertCircle, Ship, Star } from 'lucide-react';
import { tData } from '@/i18n/tData';
import { Button } from '../ui/button';
import { INCOTERMS } from '../vendor/vendorConstants';
import { IncotermAlertBell } from './IncotermAlertBell';

// Rangée de catégories + filtres incoterm/note + bandeaux (COD, tarifs adhérents) du catalogue
export const CatalogFiltersNotices = ({
  categories, selectedCategory, setSelectedCategory, products, user, navigate,
  selectedIncoterm, setSelectedIncoterm, minRating, setMinRating, sortByRating, setSortByRating,
  zoneName,
}) => (
  <>
    {/* Categories */}
    <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
      <button
        onClick={() => setSelectedCategory('all')}
        className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
          selectedCategory === 'all'
            ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
            : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
        }`}
      >
        {i18n.t('lolodrive.tous')}
      </button>
      {categories.map(cat => (
        <button
          key={cat.id}
          onClick={() => setSelectedCategory(cat.id)}
          className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
            selectedCategory === cat.id
              ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
              : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
          }`}
        >
          {tData(cat.name)}
        </button>
      ))}
    </div>

    {/* Filtre Incoterm */}
    <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1" data-testid="incoterm-filter-row">
      <span className="inline-flex items-center gap-1.5 text-xs text-white/50 shrink-0">
        <Ship className="w-3.5 h-3.5" />
        {i18n.t('catalog.livraison_incoterm', 'Livraison (incoterm)')} :
      </span>
      <button
        onClick={() => setSelectedIncoterm('all')}
        data-testid="incoterm-filter-all"
        className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
          selectedIncoterm === 'all'
            ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
            : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
        }`}
      >
        {i18n.t('lolodrive.tous')}
      </button>
      {INCOTERMS.map((inc) => (
        <button
          key={inc.code}
          onClick={() => setSelectedIncoterm(selectedIncoterm === inc.code ? 'all' : inc.code)}
          title={inc.label}
          data-testid={`incoterm-filter-${inc.code}`}
          className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide whitespace-nowrap transition-all ${
            selectedIncoterm === inc.code
              ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
              : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
          }`}
        >
          {inc.code}
        </button>
      ))}
      <IncotermAlertBell selectedIncoterm={selectedIncoterm} user={user} />

      <span className="mx-2 h-4 w-px bg-white/10 shrink-0" />

      {/* Filtre / tri par note */}
      <span className="inline-flex items-center gap-1.5 text-xs text-white/50 shrink-0">
        <Star className="w-3.5 h-3.5" />
        {i18n.t('catalog.note', 'Note')} :
      </span>
      {[3, 4].map((n) => (
        <button
          key={n}
          onClick={() => setMinRating(minRating === n ? 'all' : n)}
          data-testid={`rating-filter-${n}`}
          className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            minRating === n
              ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
              : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
          }`}
        >
          ≥ {n}★
        </button>
      ))}
      <button
        onClick={() => setSortByRating(!sortByRating)}
        data-testid="rating-sort-btn"
        className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
          sortByRating
            ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
            : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
        }`}
      >
        ★ {i18n.t('catalog.meilleures_notes', 'Meilleures notes')}
      </button>
    </div>

    {/* Règlement à Réception Pro — carte commerciale (version courte) */}
    <div className="mb-6 p-4 rounded-xl border border-[#D9B35A]/30" style={{ background: 'linear-gradient(90deg, rgba(217,179,90,0.16), rgba(217,179,90,0.03))' }} data-testid="cod-banner">
      <p className="text-sm text-white">
        <strong className="text-[#D9B35A]">🛡️ Commandez maintenant. Réglez à réception.</strong> —
        Aucun acompte sur les marchandises éligibles. Le règlement est déclenché après confirmation
        électronique de la livraison.
      </p>
      <p className="text-[11px] text-white/45 mt-1.5">
        Accès sous réserve d'éligibilité et de plafond disponible. Les commandes EXW restent payables
        à la mise à disposition ou à l'enlèvement.
      </p>
    </div>

    {/* Access Warning */}
    {products.length > 0 && !products[0].price_visible && (
      <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20" data-testid="catalog-price-locked-banner">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-amber-400">
              {user ? i18n.t('catalog.acces_limite') : i18n.t('catalog.tarifs_adherents', 'Tarifs réservés aux adhérents')}
            </p>
            {!user && zoneName && (
              <p className="text-sm text-white font-semibold mt-0.5" data-testid="visitor-zone-count">
                {products.length} {i18n.t('catalog.produits_dispo_zone', 'produit(s) disponible(s) en')} {zoneName} — {i18n.t('catalog.rejoignez_coop', 'rejoignez la coopérative pour les commander au tarif adhérent.')}
              </p>
            )}
            <p className="text-sm text-amber-400/80">
              {user
                ? i18n.t('catalog.les_prix_ne_sont')
                : i18n.t('catalog.tarifs_adherents_desc', 'Consultez librement le catalogue. Les tarifs sont visibles uniquement par les membres abonnés de la coopérative.')}
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              {!user && (
                <Button size="sm" variant="outline"
                  className="border-amber-500/40 text-amber-300 hover:bg-amber-500/10"
                  onClick={() => navigate('/connexion?redirect=/catalogue')}
                  data-testid="catalog-login-cta">
                  {i18n.t('catalog.se_connecter', 'Se connecter')}
                </Button>
              )}
              <Button size="sm"
                className="bg-amber-500 hover:bg-amber-600 text-[#2A1045] font-semibold"
                onClick={() => navigate(user ? '/tarifs' : '/adhesion')}
                data-testid="catalog-subscribe-cta">
                {user
                  ? i18n.t('catalog.voir_abonnements', 'Voir les abonnements')
                  : i18n.t('catalog.devenir_adherent', 'Devenir adhérent')}
              </Button>
            </div>
          </div>
        </div>
      </div>
    )}
  </>
);
