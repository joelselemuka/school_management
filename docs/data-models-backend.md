# Data models (backend)

## Conventions

- Beaucoup de models heritent de `SoftDeleteModel` (`actif`, `deleted_at`).
- Indexes et contraintes presentes pour integrite et perf.

## common

- `SoftDeleteModel` (abstract): `actif`, `deleted_at`
- `ActiveManager`: filtre `actif=True`

## users

- `User` (AbstractUser + SoftDeleteModel)
  - `email`, `username`, `matricule`, `phone`, `photo`, `must_change_password`
- `Parent` (1-1 User)
  - infos identite/coordonnees, `sexe`
- `Eleve` (1-1 User)
  - infos identite, `date_naissance`, `statut`
- `ParentEleve`
  - lien parent/enfant + `relation`, `reduction_percent`
- `Personnel` (1-1 User)
  - `fonction`, infos identite

## core

- `AnneeAcademique`
  - `nom`, `date_debut`, `date_fin`, dates inscriptions, `actif`
- `Periode`
  - `nom`, `trimestre`, `annee_academique`, `date_debut`, `date_fin`
- `SchoolConfiguration`
  - infos ecole, `week_type`, remises, `actif`
- `HollyDays`
  - `jour`, `date`, `description`

## academics

- `Classe`
  - `nom`, `niveau`, `annee_academique`, `responsable`
- `Cours`
  - `nom`, `code`, `classe`, `coefficient`, `annee_academique`
- `AffectationEnseignant`
  - `teacher`, `cours`, `role`, `start_date`, `end_date`
- `Bulletin`
  - `eleve`, `annee_academique`, `periode`, `moyenne_generale`, `details`, `rang`, `mention`, `classe`
- `Evaluation`
  - `cours`, `periode`, `annee_academique`, `type_evaluation`, `bareme`, `poids`, `created_by`
- `Note`
  - `eleve`, `evaluation`, `valeur`, `created_by`

## admission

- `Inscription`
  - `eleve`, `classe`, `annee_academique`, `source`, `created_by`
- `AdmissionApplication`
  - infos eleve + `classe_souhaitee`, `annee_academique`, `status`, `validated_by`
- `AdmissionGuardian`
  - `application`, infos parent, `lien`

## finance

- `CompteEleve`
  - `eleve`, `annee_academique`, `total_du`, `total_paye`
- `Frais`
  - `nom`, `classe`, `annee_academique`, `montant`, `date_limite`, `obligatoire`, `actif`
- `DetteEleve`
  - `eleve`, `frais`, montants, `statut`, `last_payment_at`
- `Paiement`
  - `reference`, `eleve`, `montant`, `mode`, `statut`, `created_by`, `confirmed_by`
- `PaiementAllocation`
  - `paiement`, `dette`, `montant`
- `Facture`
  - `numero`, `paiement`, `eleve`, `montant`, `pdf`, `date_emission`, `statut`

## attendance

- `HoraireCours`
  - `cours`, `classe`, `annee_academique`, `jour`, `heure_debut`, `heure_fin`
- `SeanceCours`
  - `horaire`, `cours`, `classe`, `annee_academique`, `date`, `type`, `is_locked`
- `Presence`
  - `eleve`, `seance`, `statut`, `remarque`
- `JustificationAbsence`
  - `presence`, `motif`, `document`, `valide`
- `DisciplineRecord`
  - `eleve`, `niveau`, `date`
- `DisciplineRule`
  - `seuil`, `niveau`, `actif`
- `Holiday`
  - `date`, `label`, `annee_academique`
- `AcademicCalendarEvent`
  - `annee_academique`, `type`, `date_debut`, `date_fin`, `classes`, `suspend_cours`
- `AttendanceSummary`
  - `eleve`, `periode`, `absences`, `retards`, `is_blocking`

## communication

- `Notification`
  - `titre`, `message`, `type`, `metadata`, `created_at`
- `NotificationUser`
  - `notification`, `user`, `is_read`, `read_at`
- `NotificationDelivery`
  - `notification_user`, `canal`, `status`, `error_message`, `sent_at`

Note: `communication.views` et `communication.serializers` referencent `NotificationPreference` et `NotificationRecipient` qui ne sont pas presents dans `communication/models.py`.

## comptabilite

- `Account`
  - `code`, `name`, `type`
- `Expense`
  - `reference`, `description`, `amount`, `statut`, `created_by`, `validated_by`
- `Transaction`
  - `reference`, `description`, `date`
- `TransactionLine`
  - `transaction`, `account`, `debit`, `credit`
- `FiscalPeriod`
  - `year`, `month`, `start_date`, `end_date`, `status`, `closed_by`

## Relations inter-apps (principales)

- `users.User` lie a `Parent`, `Eleve`, `Personnel` (1-1)
- `academics` depend de `core` (annee/period) et `users` (eleve/personnel)
- `admission` depend de `academics` (classe) et `core` (annee)
- `finance` depend de `users` (eleve) et `core`
- `attendance` depend de `academics` (classe/cours) et `core`
