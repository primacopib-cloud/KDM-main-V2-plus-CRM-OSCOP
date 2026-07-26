# Learnings — pièges rencontrés

## 2026-07-26 — PIÈGE : édits parallèles du même fichier
Deux search_replace sur le MÊME fichier dans un même batch parallèle peuvent tous deux répondre « successful » alors qu'un seul survit (race condition, vu 2× : CtaStatsPanel.jsx puis routes_pass_registration.py). RÈGLE : ne jamais mettre 2 édits du même fichier dans un batch parallèle — les séquencer, puis vérifier par grep.
