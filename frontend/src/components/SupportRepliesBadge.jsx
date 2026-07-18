import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LifeBuoy } from 'lucide-react';
import { apiCall } from '../services/http';

export const SupportRepliesBadge = ({ className = '' }) => {
  const [unread, setUnread] = useState(0);
  const isLoggedIn = !!localStorage.getItem('user');

  useEffect(() => {
    if (!isLoggedIn) return undefined;
    const load = () => apiCall('/support/my-tickets/unread-count').then((d) => setUnread(d.unread)).catch(() => {});
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [isLoggedIn]);

  if (!isLoggedIn || unread === 0) return null;

  return (
    <Link
      to="/contact"
      data-testid="support-replies-badge"
      title="Le support a répondu à votre demande"
      className={`relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors ${className}`}
    >
      <LifeBuoy className="w-4 h-4 text-[#D9B35A]" />
      <span
        className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-0.5 bg-red-500 rounded-full text-[10px] text-white font-bold flex items-center justify-center"
        data-testid="support-replies-count"
      >
        {unread > 9 ? '9+' : unread}
      </span>
    </Link>
  );
};
