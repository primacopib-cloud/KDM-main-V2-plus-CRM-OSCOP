import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const MessagesNavLink = ({ variant = 'dark' }) => {
  const [unread, setUnread] = useState(0);
  const light = variant === 'light';

  useEffect(() => {
    const load = () =>
      fetch(`${API}/api/messages/unread-count`, { credentials: 'include' })
        .then((r) => (r.ok ? r.json() : { unread: 0 }))
        .then((d) => setUnread(d.unread || 0))
        .catch(() => {});
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  return (
    <Link to="/messages" title="Messagerie interne"
      className={`relative p-2 rounded-lg transition-colors ${light ? 'hover:bg-gray-100' : 'hover:bg-white/[0.06]'}`}
      data-testid="messages-nav-link">
      <Mail className={`w-4 h-4 ${light ? 'text-gray-500' : 'text-white/70'}`} />
      {unread > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[#D9B35A] text-[#1F0A33] rounded-full text-[10px] font-bold flex items-center justify-center"
          data-testid="messages-unread-badge">
          {unread > 9 ? '9+' : unread}
        </span>
      )}
    </Link>
  );
};
