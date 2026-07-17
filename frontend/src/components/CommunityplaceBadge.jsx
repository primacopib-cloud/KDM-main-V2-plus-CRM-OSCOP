import React from 'react';
import { Store } from 'lucide-react';

const CommunityplaceBadge = ({ size = 'md', className = '' }) => {
  const compact = size === 'sm';
  return (
    <span
      data-testid="communityplace-badge"
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wider select-none ${
        compact ? 'px-2 py-0.5 text-[9px]' : 'px-2.5 py-1 text-[10px]'
      } ${className}`}
      style={{
        background: 'linear-gradient(135deg, rgba(217,179,90,0.18), rgba(76,42,110,0.12))',
        border: '1px solid rgba(212,175,55,0.55)',
        color: '#8A6A1F',
        boxShadow: '0 1px 6px rgba(217,179,90,0.25)',
        whiteSpace: 'nowrap'
      }}
      title="Communityplace — la marketplace coopérative"
    >
      <Store className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} style={{ color: '#B8860B' }} />
      Communityplace
    </span>
  );
};

export default CommunityplaceBadge;
