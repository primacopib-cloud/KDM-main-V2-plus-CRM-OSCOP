import i18n from '@/i18n';
import React, { useState } from 'react';
import {
  Package, Tag, Building2, MapPin, Scale, Ruler, Thermometer,
  Clock, Shield, FileText, Truck, Box, Leaf, Award, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, Download, Info, Zap, Wrench,
  Droplets, Flame, Globe, Calendar, CheckCircle2, XCircle, Star
} from 'lucide-react';
import { Badge } from '../ui/badge';

export const CountryFlag = ({ countryCode, size = 24 }) => {
  // Map of country codes to their flag SVG paths
  const flags = {
    FR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    ES: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#c60b1e"/>
        <rect y="150" width="900" height="300" fill="#ffc400"/>
      </svg>
    ),
    IT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#009246"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ce2b37"/>
      </svg>
    ),
    DE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#000000"/>
        <rect y="200" width="900" height="200" fill="#DD0000"/>
        <rect y="400" width="900" height="200" fill="#FFCC00"/>
      </svg>
    ),
    BE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#000000"/>
        <rect x="300" width="300" height="600" fill="#FAE042"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    NL: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#AE1C28"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#21468B"/>
      </svg>
    ),
    PT: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="360" height="600" fill="#006600"/>
        <rect x="360" width="540" height="600" fill="#FF0000"/>
        <circle cx="360" cy="300" r="100" fill="#FFCC00"/>
      </svg>
    ),
    MA: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#C1272D"/>
        <path d="M450,170 L485,295 L615,295 L510,370 L545,495 L450,420 L355,495 L390,370 L285,295 L415,295 Z" fill="none" stroke="#006233" strokeWidth="15"/>
      </svg>
    ),
    TN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#E70013"/>
        <circle cx="450" cy="300" r="150" fill="#FFFFFF"/>
        <circle cx="480" cy="300" r="120" fill="#E70013"/>
        <path d="M400,300 L450,260 L450,340 Z" fill="#E70013"/>
      </svg>
    ),
    CN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DE2910"/>
        <polygon points="150,100 170,160 230,160 180,200 200,260 150,220 100,260 120,200 70,160 130,160" fill="#FFDE00"/>
      </svg>
    ),
    TH: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="100" fill="#A51931"/>
        <rect y="100" width="900" height="100" fill="#F4F5F8"/>
        <rect y="200" width="900" height="200" fill="#2D2A4A"/>
        <rect y="400" width="900" height="100" fill="#F4F5F8"/>
        <rect y="500" width="900" height="100" fill="#A51931"/>
      </svg>
    ),
    VN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#DA251D"/>
        <polygon points="450,120 510,300 690,300 540,400 600,580 450,480 300,580 360,400 210,300 390,300" fill="#FFFF00"/>
      </svg>
    ),
    IN: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="200" fill="#FF9933"/>
        <rect y="200" width="900" height="200" fill="#FFFFFF"/>
        <rect y="400" width="900" height="200" fill="#138808"/>
        <circle cx="450" cy="300" r="60" fill="#000080"/>
      </svg>
    ),
    BR: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#009B3A"/>
        <polygon points="450,50 850,300 450,550 50,300" fill="#FEDF00"/>
        <circle cx="450" cy="300" r="100" fill="#002776"/>
      </svg>
    ),
    US: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#BF0A30"/>
        <rect y="46" width="900" height="46" fill="#FFFFFF"/>
        <rect y="138" width="900" height="46" fill="#FFFFFF"/>
        <rect y="230" width="900" height="46" fill="#FFFFFF"/>
        <rect y="322" width="900" height="46" fill="#FFFFFF"/>
        <rect y="414" width="900" height="46" fill="#FFFFFF"/>
        <rect y="506" width="900" height="46" fill="#FFFFFF"/>
        <rect width="360" height="322" fill="#002868"/>
      </svg>
    ),
    GB: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="900" height="600" fill="#012169"/>
        <path d="M0,0 L900,600 M900,0 L0,600" stroke="#FFFFFF" strokeWidth="100"/>
        <path d="M0,0 L900,600 M900,0 L0,600" stroke="#C8102E" strokeWidth="60"/>
        <path d="M450,0 V600 M0,300 H900" stroke="#FFFFFF" strokeWidth="150"/>
        <path d="M450,0 V600 M0,300 H900" stroke="#C8102E" strokeWidth="90"/>
      </svg>
    ),
    GP: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    MQ: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    GF: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
    RE: (
      <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
        <rect width="300" height="600" fill="#002395"/>
        <rect x="300" width="300" height="600" fill="#ffffff"/>
        <rect x="600" width="300" height="600" fill="#ED2939"/>
      </svg>
    ),
  };
  
  return flags[countryCode] || (
    <svg viewBox="0 0 900 600" width={size} height={size * 0.67} className="inline-block rounded shadow-sm">
      <rect width="900" height="600" fill="#cccccc"/>
      <text x="450" y="320" textAnchor="middle" fontSize="200" fill="#666666">{countryCode}</text>
    </svg>
  );
};

// Format currency
export const formatCurrency = (cents, currency = 'EUR') => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency: currency
  }).format(cents / 100);
};

// Get category label
export const getCategoryLabel = (category) => {
  const labels = {
    alimentaire: 'Alimentaire',
    boissons: 'Boissons',
    materiaux: 'Matériaux',
    equipements: 'Équipements',
    matieres_premieres: 'Matières premières',
    hygiene: 'Hygiène',
    chimie: 'Chimie',
    textile: 'Textile',
    electronique: 'Électronique',
    autre: 'Autre'
  };
  return labels[category] || category;
};

// Get status badge
export const getStatusBadge = (status) => {
  const config = {
    draft: { label: 'Brouillon', class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
    pending_approval: { label: 'En attente', class: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
    approved: { label: 'Approuvé', class: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
    rejected: { label: 'Rejeté', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
    discontinued: { label: 'Arrêté', class: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    out_of_stock: { label: 'Rupture', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' }
  };
  return config[status] || config.draft;
};

// Get temperature label
export const getTemperatureLabel = (range) => {
  const labels = {
    ambient: 'Température ambiante (15-25°C)',
    refrigerated: 'Réfrigéré (0-4°C)',
    frozen: 'Surgelé (-18°C)',
    deep_frozen: 'Surgélation profonde (-25°C)',
    controlled: 'Température contrôlée'
  };
  return labels[range] || range;
};

// Section component
export const Section = ({ title, icon: Icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-white/[0.08] rounded-xl overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="w-5 h-5 text-[#D9B35A]" />}
          <span className="font-semibold text-white">{title}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
      </button>
      {isOpen && (
        <div className="p-4 border-t border-white/[0.08]">
          {children}
        </div>
      )}
    </div>
  );
};

// Data row component
export const DataRow = ({ label, value, icon: Icon, highlight = false }) => {
  if (!value && value !== 0) return null;
  
  return (
    <div className={`flex justify-between items-center py-2 ${highlight ? 'bg-[#D9B35A]/10 -mx-2 px-2 rounded-lg' : ''}`}>
      <span className="text-white/60 flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4" />}
        {label}
      </span>
      <span className={`font-medium ${highlight ? 'text-[#D9B35A]' : 'text-white/90'}`}>{value}</span>
    </div>
  );
};

// Main component
