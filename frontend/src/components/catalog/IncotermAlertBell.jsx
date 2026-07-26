import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bell, BellRing, SlidersHorizontal } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Cloche « M'alerter » sur l'incoterm sélectionné + raccourci vers le centre d'alertes
export const IncotermAlertBell = ({ selectedIncoterm, user }) => {
  const [codes, setCodes] = useState([]);

  useEffect(() => {
    if (!user) return;
    fetch(`${API_URL}/api/v2/catalog/incoterm-alerts`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setCodes(d.codes || []))
      .catch(() => {});
  }, [user]);

  if (!user) return null;
  const active = codes.includes(selectedIncoterm);

  const toggle = async () => {
    const next = active ? codes.filter((c) => c !== selectedIncoterm) : [...codes, selectedIncoterm];
    try {
      const r = await fetch(`${API_URL}/api/v2/catalog/incoterm-alerts`, {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codes: next }),
      });
      if (!r.ok) throw new Error();
      setCodes(next);
      toast.success(active
        ? i18n.t('catalog.alerte_off', `Alerte ${selectedIncoterm} désactivée`)
        : i18n.t('catalog.alerte_on', `Vous serez prévenu des nouveaux produits livrables en ${selectedIncoterm}`));
    } catch {
      toast.error(i18n.t('catalog.alerte_erreur', "Impossible de mettre à jour l'alerte"));
    }
  };

  return (
    <>
      {selectedIncoterm !== 'all' && (
        <button
          type="button"
          onClick={toggle}
          data-testid={`incoterm-alert-bell-${selectedIncoterm}`}
          title={active
            ? i18n.t('catalog.alerte_active_tip', 'Alerte active — cliquez pour la désactiver')
            : i18n.t('catalog.alerte_tip', 'Être prévenu des nouveaux produits avec cet incoterm')}
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition-all ${
            active
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
              : 'bg-white/[0.04] text-white/60 hover:text-white border-white/[0.08]'
          }`}
        >
          {active ? <BellRing className="w-3.5 h-3.5" /> : <Bell className="w-3.5 h-3.5" />}
          {active
            ? i18n.t('catalog.alerte_active', 'Alerte activée')
            : i18n.t('catalog.malerter', `M'alerter (${selectedIncoterm})`)}
        </button>
      )}
      <Link
        to="/alertes-favoris"
        data-testid="alerts-center-link"
        title={i18n.t('catalog.gerer_alertes_tip', 'Ouvrir le centre de préférences des alertes')}
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition-all bg-white/[0.04] hover:text-white border-white/[0.08] ${
          codes.length ? 'text-emerald-400/90' : 'text-white/60'
        }`}
      >
        <SlidersHorizontal className="w-3.5 h-3.5" />
        {i18n.t('catalog.gerer_alertes', 'Gérer mes alertes')}
        {codes.length > 0 && (
          <span className="px-1.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">{codes.length}</span>
        )}
      </Link>
    </>
  );
};
