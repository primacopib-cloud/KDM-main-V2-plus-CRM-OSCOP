import i18n from './index';

const slug = (t) =>
  t.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

export const tData = (text) => {
  if (!text || typeof text !== 'string') return text;
  const key = `data.${slug(text)}`;
  const translated = i18n.t(key);
  return translated === key ? text : translated;
};
