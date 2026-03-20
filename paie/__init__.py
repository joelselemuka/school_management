"""
Module Paie — Gestion de la paie du personnel scolaire.

Ce module prend en charge :
  - ContratEmploye  : contrat de travail avec salaire de base, taux de retenue,
                      taux heures sup, prime de motivation.
  - BulletinSalaire : bulletin mensuel calculé automatiquement.
  - PaiementSalaire : paiement lié à un bulletin (traçabilité comptable OHADA).

API endpoints :
  /api/v1/paie/contrats/   — CRUD contrats + actions (résilier, simuler, actif)
  /api/v1/paie/bulletins/  — Cycle de vie bulletin (générer, valider, payer, masse)
  /api/v1/paie/salaires/   — Paiements de salaire (confirmer, annuler, historique)
"""
