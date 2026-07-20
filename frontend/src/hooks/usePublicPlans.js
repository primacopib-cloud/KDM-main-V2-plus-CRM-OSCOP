import { useEffect, useState } from 'react';
import { subscriptionPlans as fallbackPlans } from '../data/mock';

let cache = null;

export const usePublicPlans = () => {
  const [plans, setPlans] = useState(cache);

  useEffect(() => {
    if (cache) return;
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/plans`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && Array.isArray(d.plans) && d.plans.length) {
          cache = d.plans.map((p) => ({
            ...p,
            id: p.id || p.slug,
            price: p.price ?? Math.round((p.price_cents || 0) / 100),
          }));
          setPlans(cache);
        }
      })
      .catch(() => {});
  }, []);

  return { plans: plans || fallbackPlans, loaded: !!plans };
};
