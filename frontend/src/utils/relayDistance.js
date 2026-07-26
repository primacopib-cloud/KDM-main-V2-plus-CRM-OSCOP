export const DISTANCE_FEE_NEAR_UC = 0.05;
export const DISTANCE_FEE_FAR_UC = 0.08;
export const DISTANCE_FEE_OUT_UC = 0.13;

export const haversineKm = (lat1, lng1, lat2, lng2) => {
  const rad = (d) => (d * Math.PI) / 180;
  const a = Math.sin(rad(lat2 - lat1) / 2) ** 2
    + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lng2 - lng1) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
};

export const distanceFeeRate = (refPoint, point) => {
  if (!refPoint || !point || refPoint.code === point.code) return 0;
  if ((refPoint.territory || '').toUpperCase() !== (point.territory || '').toUpperCase()) return DISTANCE_FEE_OUT_UC;
  if ([refPoint.lat, refPoint.lng, point.lat, point.lng].some((c) => c == null)) return DISTANCE_FEE_NEAR_UC;
  return haversineKm(refPoint.lat, refPoint.lng, point.lat, point.lng) <= 50
    ? DISTANCE_FEE_NEAR_UC : DISTANCE_FEE_FAR_UC;
};

export const kmBetween = (refPoint, point) => {
  if (!refPoint || !point || refPoint.code === point.code) return null;
  if ([refPoint.lat, refPoint.lng, point.lat, point.lng].some((c) => c == null)) return null;
  return Math.round(haversineKm(refPoint.lat, refPoint.lng, point.lat, point.lng));
};

export const getReferencePointCode = () => {
  try { return JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null')?.code || null; } catch { return null; }
};
