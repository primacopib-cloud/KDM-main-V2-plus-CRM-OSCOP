import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const TOKEN = process.env.REACT_APP_MAPBOX_TOKEN;
if (TOKEN) mapboxgl.accessToken = TOKEN;

const TERRITORY_DEFAULTS = {
  GP: { lat: 16.2650, lng: -61.5510, zoom: 9.5 },
  MQ: { lat: 14.6415, lng: -61.0242, zoom: 10 },
  GF: { lat: 4.0000, lng: -53.0000, zoom: 7 },
  RE: { lat: -21.1151, lng: 55.5364, zoom: 10 },
  ALL: { lat: 7.5, lng: -3.0, zoom: 1.5 }, // fallback world
};

/**
 * Carte interactive des relais LOLODRIVE (Mapbox GL).
 * Props :
 *   - points: [{id, name, code, lat, lng, city, territory, status}, ...]
 *   - territory: 'GP' | 'MQ' | 'GF' | 'RE' | null  → recadre la vue
 *   - onSelect(point): callback clic marqueur
 *   - height: '420px' (par défaut)
 */
export default function LoloPointsMap({ points = [], territory = null, onSelect, height = '460px' }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);

  // Initial map setup (run once)
  useEffect(() => {
    if (!TOKEN) return;
    if (mapRef.current || !containerRef.current) return;
    const init = TERRITORY_DEFAULTS[territory] || TERRITORY_DEFAULTS.GP;
    mapRef.current = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [init.lng, init.lat],
      zoom: init.zoom,
      attributionControl: true,
    });
    mapRef.current.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recenter on territory change
  useEffect(() => {
    if (!mapRef.current) return;
    const conf = TERRITORY_DEFAULTS[territory] || TERRITORY_DEFAULTS.ALL;
    mapRef.current.flyTo({ center: [conf.lng, conf.lat], zoom: conf.zoom, speed: 1.4 });
  }, [territory]);

  // Update markers when points change
  useEffect(() => {
    if (!mapRef.current) return;
    // Clear previous markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const filtered = points.filter((p) => typeof p.lat === 'number' && typeof p.lng === 'number');
    if (filtered.length === 0) return;

    filtered.forEach((p) => {
      const el = document.createElement('div');
      el.className = 'kdm-lolo-marker';
      el.setAttribute('data-testid', `map-marker-${p.code}`);
      el.style.cssText = `
        width: 28px; height: 28px; border-radius: 50%;
        background: linear-gradient(135deg, #D9B35A, #7c3aed);
        border: 2px solid rgba(255,255,255,0.9);
        box-shadow: 0 2px 8px rgba(0,0,0,0.6);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
        color: #000; font-weight: 700; font-size: 11px;
      `;
      el.textContent = p.territory || '•';

      const popup = new mapboxgl.Popup({ offset: 18, closeButton: false }).setHTML(`
        <div style="font-family: system-ui; min-width: 200px; padding: 4px 0;">
          <div style="font-weight: 700; font-size: 14px; color: #0f172a;">${escapeHtml(p.name)}</div>
          <div style="font-size: 11px; color: #64748b; margin: 4px 0; font-family: monospace;">${escapeHtml(p.code)} · ${escapeHtml(p.territory || '?')}</div>
          <div style="font-size: 12px; color: #1e293b;">${escapeHtml(p.address || '')}</div>
          <div style="font-size: 12px; color: #1e293b;">${escapeHtml(p.city || '')}</div>
          ${p.zone_name ? `<div style="font-size: 11px; color: #64748b; margin-top: 4px;">Zone: ${escapeHtml(p.zone_name)}</div>` : ''}
        </div>
      `);

      const marker = new mapboxgl.Marker({ element: el }).setLngLat([p.lng, p.lat]).setPopup(popup).addTo(mapRef.current);
      el.addEventListener('click', () => onSelect?.(p));
      markersRef.current.push(marker);
    });

    // Auto-fit bounds when no territory filter or several points
    if (!territory && filtered.length > 1) {
      const bounds = new mapboxgl.LngLatBounds();
      filtered.forEach((p) => bounds.extend([p.lng, p.lat]));
      mapRef.current.fitBounds(bounds, { padding: 60, maxZoom: 8, duration: 800 });
    }
  }, [points, territory, onSelect]);

  if (!TOKEN) {
    return (
      <div
        data-testid="map-no-token"
        className="rounded-xl border border-white/10 bg-white/[0.03] p-8 text-center text-white/60"
        style={{ height }}
      >
        Carte indisponible : `REACT_APP_MAPBOX_TOKEN` non configuré.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="lolo-points-map"
      className="rounded-xl overflow-hidden border border-white/10"
      style={{ width: '100%', height }}
    />
  );
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
