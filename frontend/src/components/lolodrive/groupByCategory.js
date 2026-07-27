// Regroupe une liste de produits en Catégorie → Sous-catégorie (ordre alphabétique, "Autres" en dernier)
export const groupByCategory = (products) => {
  const cats = new Map();
  for (const p of products) {
    const cat = p.category || 'Autres';
    const sub = p.subcategory || 'Autres';
    if (!cats.has(cat)) cats.set(cat, new Map());
    const subs = cats.get(cat);
    if (!subs.has(sub)) subs.set(sub, []);
    subs.get(sub).push(p);
  }
  const sortKey = (a, b) => (a === 'Autres' ? 1 : b === 'Autres' ? -1 : a.localeCompare(b));
  return [...cats.keys()].sort(sortKey).map((cat) => ({
    category: cat,
    subs: [...cats.get(cat).keys()].sort(sortKey).map((sub) => ({
      name: sub,
      items: cats.get(cat).get(sub),
    })),
  }));
};
