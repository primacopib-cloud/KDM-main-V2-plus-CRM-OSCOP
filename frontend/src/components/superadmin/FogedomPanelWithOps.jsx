import { useEffect, useState } from 'react';
import { API, getAuthHeaders } from '../../services/http';
import { FogedomPanel } from './FogedomPanel';

export const FogedomPanelWithOps = () => {
  const [ops, setOps] = useState([]);
  useEffect(() => {
    fetch(`${API}/admin/purchase-resale/operations`, { headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((d) => setOps(d.operations || []))
      .catch(() => {});
  }, []);
  return <FogedomPanel operations={ops} />;
};
