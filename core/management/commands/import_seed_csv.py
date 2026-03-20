import csv
from pathlib import Path
from datetime import datetime, time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from users.models import User, Parent, Eleve, Personnel, ParentEleve
from core.models import AnneeAcademique, Periode
from academics.models import Classe, Cours, Evaluation, Note
from admission.models import Inscription
from finance.models import Paiement, Facture, Frais, DetteEleve, PaiementAllocation, CompteEleve
from communication.models import Notification, NotificationUser, NotificationDelivery
from attendance.models import HoraireCours, SeanceCours, Presence


DEFAULT_SEED_DIR = Path(settings.BASE_DIR) / "_bmad-output" / "planning-artifacts"

ORDERED_FILES = [
    "seed-users.csv",
    "seed-parents.csv",
    "seed-personnel.csv",
    "seed-students.csv",
    "seed-parent-eleve.csv",
    "seed-years.csv",
    "seed-periods.csv",
    "seed-classes.csv",
    "seed-courses.csv",
    "seed-frais.csv",
    "seed-enrollments.csv",
    "seed-dettes.csv",
    "seed-evaluations.csv",
    "seed-grades.csv",
    "seed-attendance.csv",
    "seed-compte-eleve.csv",
    "seed-payments.csv",
    "seed-paiement-allocations.csv",
    "seed-invoices.csv",
    "seed-notifications.csv",
    "seed-notification-users.csv",
    "seed-notification-deliveries.csv",
    "seed-roles.csv",
    "seed-chat.csv",
    "seed-audit.csv",
]

REQUIRED_COLUMNS = {
    "seed-users.csv": ["username", "matricule", "email", "first_name", "last_name", "is_superuser", "is_staff", "password"],
    "seed-parents.csv": ["username", "nom", "postnom", "prenom", "telephone", "adresse", "sexe"],
    "seed-personnel.csv": ["username", "fonction", "nom", "postnom", "prenom", "telephone", "date_naissance", "lieu_naissance", "adresse", "sexe"],
    "seed-students.csv": ["username", "nom", "postnom", "prenom", "date_naissance", "lieu_naissance", "adresse", "statut", "sexe"],
    "seed-parent-eleve.csv": ["parent_username", "student_username", "relation", "reduction_percent"],
    "seed-years.csv": ["nom", "date_debut", "date_fin", "date_debut_inscriptions", "date_fin_inscriptions", "actif"],
    "seed-periods.csv": ["nom", "trimestre", "annee_nom", "date_debut", "date_fin", "actif"],
    "seed-classes.csv": ["class_code", "nom", "niveau", "annee_nom", "responsable_username"],
    "seed-courses.csv": ["course_code", "nom", "classe_code", "annee_nom", "coefficient"],
    "seed-frais.csv": ["nom", "classe_code", "annee_nom", "montant", "date_limite", "obligatoire", "actif"],
    "seed-enrollments.csv": ["student_username", "classe_code", "annee_nom", "created_by_username", "source"],
    "seed-dettes.csv": ["student_username", "frais_nom", "classe_code", "annee_nom", "montant_initial", "montant_reduit", "montant_paye", "montant_du", "statut"],
    "seed-evaluations.csv": ["evaluation_id", "course_code", "periode_nom", "annee_nom", "type_evaluation", "nom", "bareme", "poids", "created_by_username"],
    "seed-grades.csv": ["evaluation_id", "student_username", "valeur", "created_by_username"],
    "seed-attendance.csv": ["date", "course_code", "classe_code", "annee_nom", "student_username", "statut"],
    "seed-compte-eleve.csv": ["student_username", "annee_nom", "total_du", "total_paye"],
    "seed-payments.csv": ["reference", "student_username", "montant", "mode", "statut", "created_by_username", "confirmed_by_username", "confirmed_at"],
    "seed-paiement-allocations.csv": ["payment_reference", "student_username", "frais_nom", "classe_code", "annee_nom", "montant"],
    "seed-invoices.csv": ["numero", "payment_reference", "student_username", "montant", "date_emission", "statut"],
    "seed-notifications.csv": ["notification_id", "titre", "message", "type", "created_at"],
    "seed-notification-users.csv": ["notification_id", "username", "is_read", "read_at"],
    "seed-notification-deliveries.csv": ["notification_id", "username", "canal", "status", "error_message", "sent_at"],
    "seed-roles.csv": ["username", "roles"],
    "seed-chat.csv": ["conversation_id", "type", "participants", "message", "created_at"],
    "seed-audit.csv": ["event_id", "actor_username", "action", "object_type", "object_id", "created_at", "ip"],
}


class RollbackDryRun(Exception):
    pass


class RollbackFile(Exception):
    pass


class Command(BaseCommand):
    help = "Importe des fichiers CSV de seed (planning-artifacts)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_SEED_DIR),
            help="Dossier contenant les CSV de seed.",
        )
        parser.add_argument(
            "--only",
            nargs="*",
            default=None,
            help="Importer uniquement ces fichiers (noms CSV).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule l'import sans persister en base.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Ignore les lignes deja presentes (aucune mise a jour).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Echoue a la premiere erreur.",
        )

    def handle(self, *args, **options):
        seed_dir = Path(options["dir"])
        only = options["only"]
        dry_run = options["dry_run"]
        self.skip_existing = options["skip_existing"]
        strict = options["strict"]

        if not seed_dir.exists():
            self.stdout.write(self.style.ERROR(f"Dossier introuvable: {seed_dir}"))
            return

        self.eval_by_id = {}
        self.notif_by_id = {}
        self.errors = []

        files = ORDERED_FILES if not only else [f for f in ORDERED_FILES if f in only]

        try:
            if dry_run:
                with transaction.atomic():
                    for filename in files:
                        path = seed_dir / filename
                        if not path.exists():
                            continue
                        rows = self._read_csv(path)
                        if not rows:
                            continue
                        if not self._validate_headers(filename, rows, strict):
                            continue
                        self._dispatch(filename, rows, strict)
                    raise RollbackDryRun()
            else:
                for filename in files:
                    path = seed_dir / filename
                    if not path.exists():
                        continue
                    rows = self._read_csv(path)
                    if not rows:
                        continue
                    if not self._validate_headers(filename, rows, strict):
                        continue
                    self._dispatch(filename, rows, strict)
        except RollbackDryRun:
            self.stdout.write(self.style.WARNING("Dry-run: aucun changement en base."))

        if self.errors:
            self.stdout.write(self.style.WARNING("Erreurs detectees:"))
            for e in self.errors:
                self.stdout.write(f"- {e}")

    def _read_csv(self, path: Path):
        with path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _validate_headers(self, filename, rows, strict):
        required = REQUIRED_COLUMNS.get(filename)
        if not required or not rows:
            return True
        headers = set(rows[0].keys())
        missing = [c for c in required if c not in headers]
        if missing:
            self._error(f"{filename}: colonnes manquantes {missing}", strict)
            return False
        return True

    def _dispatch(self, filename, rows, strict):
        handlers = {
            "seed-users.csv": self._import_users,
            "seed-parents.csv": self._import_parents,
            "seed-personnel.csv": self._import_personnel,
            "seed-students.csv": self._import_students,
            "seed-parent-eleve.csv": self._import_parent_eleve,
            "seed-years.csv": self._import_years,
            "seed-periods.csv": self._import_periods,
            "seed-classes.csv": self._import_classes,
            "seed-courses.csv": self._import_courses,
            "seed-frais.csv": self._import_frais,
            "seed-enrollments.csv": self._import_enrollments,
            "seed-dettes.csv": self._import_dettes,
            "seed-evaluations.csv": self._import_evaluations,
            "seed-grades.csv": self._import_grades,
            "seed-attendance.csv": self._import_attendance,
            "seed-compte-eleve.csv": self._import_compte_eleve,
            "seed-payments.csv": self._import_payments,
            "seed-paiement-allocations.csv": self._import_paiement_allocations,
            "seed-invoices.csv": self._import_invoices,
            "seed-notifications.csv": self._import_notifications,
            "seed-notification-users.csv": self._import_notification_users,
            "seed-notification-deliveries.csv": self._import_notification_deliveries,
            "seed-roles.csv": self._skip_roles,
            "seed-chat.csv": self._skip_chat,
            "seed-audit.csv": self._skip_audit,
        }

        handler = handlers.get(filename)
        if not handler:
            self.stdout.write(self.style.WARNING(f"Fichier ignore: {filename}"))
            return

        self.file_errors = []
        try:
            with transaction.atomic():
                handler(rows, strict)
                if self.file_errors:
                    raise RollbackFile()
        except RollbackFile:
            self.stdout.write(self.style.WARNING(f"Rollback fichier (erreurs): {filename}"))
        except Exception as exc:
            if strict:
                raise
            self.stdout.write(self.style.WARNING(f"Echec fichier: {filename} ({exc})"))
            return

        if not self.file_errors:
            self.stdout.write(self.style.SUCCESS(f"Import OK: {filename}"))

    def _error(self, message, strict):
        if strict:
            raise Exception(message)
        self.errors.append(message)
        self.file_errors.append(message)

    def _require_fields(self, row, fields, strict):
        for f in fields:
            if row.get(f) in (None, ""):
                self._error(f"Champ obligatoire manquant: {f}", strict)
                return False
        return True

    def _bool(self, value, default=False):
        if value is None or value == "":
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def _parse_date(self, value, field, strict):
        if not value:
            self._error(f"Date manquante: {field}", strict)
            return None
        d = parse_date(value)
        if not d:
            self._error(f"Date invalide pour {field}: {value}", strict)
        return d

    def _parse_datetime(self, value, field, strict):
        if not value:
            self._error(f"Datetime manquant: {field}", strict)
            return None
        dt = parse_datetime(value)
        if dt:
            return dt
        d = parse_date(value)
        if not d:
            self._error(f"Datetime invalide pour {field}: {value}", strict)
            return None
        return datetime.combine(d, time(0, 0))

    def _parse_decimal(self, value, field, strict):
        if value is None or value == "":
            self._error(f"Valeur decimale manquante: {field}", strict)
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            self._error(f"Valeur decimale invalide pour {field}: {value}", strict)
            return None

    def _parse_int(self, value, field, strict):
        if value is None or value == "":
            self._error(f"Valeur entiere manquante: {field}", strict)
            return None
        try:
            return int(value)
        except ValueError:
            self._error(f"Valeur entiere invalide pour {field}: {value}", strict)
            return None

    def _get_user(self, username, strict):
        if not username:
            self._error("username manquant", strict)
            return None
        user = User.objects.filter(username=username).first()
        if not user:
            self._error(f"Utilisateur introuvable: {username}", strict)
        return user
    def _import_users(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-users.csv"], strict):
                continue
            username = r.get("username")
            matricule = r.get("matricule") or username
            email = r.get("email") or None
            first_name = r.get("first_name") or ""
            last_name = r.get("last_name") or ""
            is_superuser = self._bool(r.get("is_superuser"))
            is_staff = self._bool(r.get("is_staff"))
            password = r.get("password") or None

            existing = User.objects.filter(username=username).first()
            if existing and self.skip_existing:
                if password:
                    existing.set_password(password)
                    existing.save()
                continue

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "matricule": matricule,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_superuser": is_superuser,
                    "is_staff": is_staff,
                },
            )
            if not created and not self.skip_existing:
                user.matricule = matricule
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.is_superuser = is_superuser
                user.is_staff = is_staff
            if password:
                user.set_password(password)
            user.save()

    def _import_parents(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-parents.csv"], strict):
                continue
            user = self._get_user(r.get("username"), strict)
            if not user:
                continue
            if self.skip_existing and Parent.objects.filter(user=user).exists():
                continue
            Parent.objects.update_or_create(
                user=user,
                defaults={
                    "nom": r.get("nom") or "",
                    "postnom": r.get("postnom") or "",
                    "prenom": r.get("prenom") or "",
                    "telephone": r.get("telephone") or "",
                    "adresse": r.get("adresse") or "",
                    "sexe": r.get("sexe") or "masculin",
                },
            )

    def _import_personnel(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-personnel.csv"], strict):
                continue
            user = self._get_user(r.get("username"), strict)
            if not user:
                continue
            if self.skip_existing and Personnel.objects.filter(user=user).exists():
                continue
            Personnel.objects.update_or_create(
                user=user,
                defaults={
                    "fonction": r.get("fonction") or "enseignant",
                    "nom": r.get("nom") or "",
                    "postnom": r.get("postnom") or "",
                    "prenom": r.get("prenom") or "",
                    "specialite": r.get("specialite") or "",
                    "telephone": r.get("telephone") or "",
                    "date_naissance": self._parse_date(r.get("date_naissance"), "date_naissance", strict),
                    "lieu_naissance": r.get("lieu_naissance") or "",
                    "adresse": r.get("adresse") or "",
                    "sexe": r.get("sexe") or "masculin",
                },
            )

    def _import_students(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-students.csv"], strict):
                continue
            user = self._get_user(r.get("username"), strict)
            if not user:
                continue
            if self.skip_existing and Eleve.objects.filter(user=user).exists():
                continue
            Eleve.objects.update_or_create(
                user=user,
                defaults={
                    "nom": r.get("nom") or "",
                    "postnom": r.get("postnom") or "",
                    "prenom": r.get("prenom") or "",
                    "date_naissance": self._parse_date(r.get("date_naissance"), "date_naissance", strict),
                    "lieu_naissance": r.get("lieu_naissance") or "",
                    "adresse": r.get("adresse") or "",
                    "statut": r.get("statut") or "actif",
                    "sexe": r.get("sexe") or "masculin",
                },
            )

    def _import_parent_eleve(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-parent-eleve.csv"], strict):
                continue
            parent_user = self._get_user(r.get("parent_username"), strict)
            eleve_user = self._get_user(r.get("student_username"), strict)
            if not parent_user or not eleve_user:
                continue
            parent = Parent.objects.filter(user=parent_user).first()
            eleve = Eleve.objects.filter(user=eleve_user).first()
            if not parent or not eleve:
                self._error("Parent ou Eleve introuvable pour ParentEleve", strict)
                continue
            if self.skip_existing and ParentEleve.objects.filter(parent=parent, eleve=eleve).exists():
                continue
            ParentEleve.objects.get_or_create(
                parent=parent,
                eleve=eleve,
                defaults={
                    "relation": r.get("relation") or "",
                    "reduction_percent": float(r.get("reduction_percent") or 0),
                },
            )

    def _import_years(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-years.csv"], strict):
                continue
            nom = r.get("nom")
            if self.skip_existing and AnneeAcademique.objects.filter(nom=nom).exists():
                continue
            defaults = {
                "date_debut": self._parse_date(r.get("date_debut"), "date_debut", strict),
                "date_fin": self._parse_date(r.get("date_fin"), "date_fin", strict),
                "date_debut_inscriptions": self._parse_date(r.get("date_debut_inscriptions"), "date_debut_inscriptions", strict),
                "date_fin_inscriptions": self._parse_date(r.get("date_fin_inscriptions"), "date_fin_inscriptions", strict),
                "actif": self._bool(r.get("actif"), True),
            }
            year, _ = AnneeAcademique.objects.update_or_create(
                nom=nom,
                defaults=defaults,
            )
            year.save()

    def _import_periods(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-periods.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            if not annee:
                self._error(f"AnneeAcademique introuvable: {r.get('annee_nom')}", strict)
                continue
            if self.skip_existing and Periode.objects.filter(nom=r.get("nom"), annee_academique=annee).exists():
                continue
            periode, _ = Periode.objects.update_or_create(
                nom=r.get("nom"),
                annee_academique=annee,
                defaults={
                    "trimestre": r.get("trimestre") or "trimestre_1",
                    "date_debut": self._parse_date(r.get("date_debut"), "date_debut", strict),
                    "date_fin": self._parse_date(r.get("date_fin"), "date_fin", strict),
                    "actif": self._bool(r.get("actif"), True),
                },
            )
            periode.save()

    def _import_classes(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-classes.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            if not annee:
                self._error(f"AnneeAcademique introuvable: {r.get('annee_nom')}", strict)
                continue
            responsable = None
            if r.get("responsable_username"):
                resp_user = self._get_user(r.get("responsable_username"), strict)
                if resp_user:
                    responsable = Personnel.objects.filter(user=resp_user).first()
            if self.skip_existing and Classe.objects.filter(nom=r.get("nom") or r.get("class_code"), annee_academique=annee).exists():
                continue
            Classe.objects.update_or_create(
                nom=r.get("nom") or r.get("class_code"),
                annee_academique=annee,
                defaults={
                    "niveau": r.get("niveau") or "primaire",
                    "responsable": responsable,
                },
            )

    def _import_courses(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-courses.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            if not annee:
                self._error(f"AnneeAcademique introuvable: {r.get('annee_nom')}", strict)
                continue
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            if not classe:
                self._error(f"Classe introuvable: {r.get('classe_code')}", strict)
                continue
            if self.skip_existing and Cours.objects.filter(code=r.get("course_code")).exists():
                continue
            coefficient = self._parse_decimal(r.get("coefficient"), "coefficient", strict)
            Cours.objects.update_or_create(
                code=r.get("course_code"),
                nom=r.get("nom") or r.get("course_code"),
                defaults={
                    "classe": classe,
                    "annee_academique": annee,
                    "coefficient": coefficient or 1,
                },
            )

    def _import_frais(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-frais.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            if not annee:
                self._error(f"AnneeAcademique introuvable: {r.get('annee_nom')}", strict)
                continue
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            if not classe:
                self._error(f"Classe introuvable: {r.get('classe_code')}", strict)
                continue
            if self.skip_existing and Frais.objects.filter(nom=r.get("nom"), classe=classe, annee_academique=annee).exists():
                continue
            Frais.objects.update_or_create(
                nom=r.get("nom"),
                classe=classe,
                annee_academique=annee,
                defaults={
                    "montant": self._parse_decimal(r.get("montant"), "montant", strict) or 0,
                    "date_limite": self._parse_date(r.get("date_limite"), "date_limite", strict),
                    "obligatoire": self._bool(r.get("obligatoire"), True),
                    "actif": self._bool(r.get("actif"), True),
                },
            )

    def _import_enrollments(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-enrollments.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            user = self._get_user(r.get("student_username"), strict)
            created_by = self._get_user(r.get("created_by_username"), strict)
            if not (annee and classe and user):
                self._error("Inscription: references manquantes", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour inscription", strict)
                continue
            if self.skip_existing and Inscription.objects.filter(eleve=eleve, annee_academique=annee).exists():
                continue
            Inscription.objects.get_or_create(
                eleve=eleve,
                annee_academique=annee,
                defaults={
                    "classe": classe,
                    "created_by": created_by,
                    "source": r.get("source") or "BUREAU",
                },
            )
    def _import_dettes(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-dettes.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            if not (annee and classe):
                self._error("Dette: annee ou classe introuvable", strict)
                continue
            frais = Frais.objects.filter(nom=r.get("frais_nom"), classe=classe, annee_academique=annee).first()
            user = self._get_user(r.get("student_username"), strict)
            if not (frais and user):
                self._error("Dette: frais ou eleve introuvable", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour dette", strict)
                continue
            if self.skip_existing and DetteEleve.objects.filter(eleve=eleve, frais=frais).exists():
                continue
            DetteEleve.objects.update_or_create(
                eleve=eleve,
                frais=frais,
                defaults={
                    "montant_initial": self._parse_decimal(r.get("montant_initial"), "montant_initial", strict) or 0,
                    "montant_reduit": self._parse_decimal(r.get("montant_reduit"), "montant_reduit", strict) or 0,
                    "montant_paye": self._parse_decimal(r.get("montant_paye"), "montant_paye", strict) or 0,
                    "montant_du": self._parse_decimal(r.get("montant_du"), "montant_du", strict) or 0,
                    "statut": r.get("statut") or "IMPAYE",
                },
            )

    def _import_evaluations(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-evaluations.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            periode = Periode.objects.filter(nom=r.get("periode_nom"), annee_academique=annee).first()
            cours = Cours.objects.filter(code=r.get("course_code")).first()
            created_by = self._get_user(r.get("created_by_username"), strict)
            if not (annee and periode and cours and created_by):
                self._error("Evaluation: references manquantes", strict)
                continue
            existing = Evaluation.objects.filter(nom=r.get("nom"), cours=cours, periode=periode, annee_academique=annee).first()
            if existing and self.skip_existing:
                self.eval_by_id[r.get("evaluation_id")] = existing
                continue
            evaluation, _ = Evaluation.objects.get_or_create(
                nom=r.get("nom"),
                cours=cours,
                periode=periode,
                annee_academique=annee,
                defaults={
                    "type_evaluation": r.get("type_evaluation") or "autre",
                    "bareme": self._parse_int(r.get("bareme"), "bareme", strict) or 20,
                    "poids": self._parse_decimal(r.get("poids"), "poids", strict) or 1,
                    "created_by": created_by,
                },
            )
            self.eval_by_id[r.get("evaluation_id")] = evaluation

    def _import_grades(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-grades.csv"], strict):
                continue
            evaluation = self.eval_by_id.get(r.get("evaluation_id"))
            if not evaluation:
                self._error(f"Evaluation introuvable: {r.get('evaluation_id')}", strict)
                continue
            user = self._get_user(r.get("student_username"), strict)
            created_by = self._get_user(r.get("created_by_username"), strict)
            if not (user and created_by):
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour note", strict)
                continue
            if self.skip_existing and Note.objects.filter(eleve=eleve, evaluation=evaluation).exists():
                continue
            Note.objects.update_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    "valeur": self._parse_decimal(r.get("valeur"), "valeur", strict) or 0,
                    "created_by": created_by,
                },
            )

    def _import_attendance(self, rows, strict):
        weekday_map = {
            0: "LUNDI",
            1: "MARDI",
            2: "MERCREDI",
            3: "JEUDI",
            4: "VENDREDI",
            5: "SAMEDI",
            6: "SAMEDI",
        }
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-attendance.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            cours = Cours.objects.filter(code=r.get("course_code")).first()
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            user = self._get_user(r.get("student_username"), strict)
            if not (annee and cours and classe and user):
                self._error("Presence: references manquantes", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour presence", strict)
                continue
            d = self._parse_date(r.get("date"), "date", strict)
            jour = weekday_map.get(d.weekday()) if d else "LUNDI"
            horaire, _ = HoraireCours.objects.get_or_create(
                cours=cours,
                classe=classe,
                annee_academique=annee,
                jour=jour,
                heure_debut=time(8, 0),
                heure_fin=time(9, 0),
                defaults={"salle": "S1"},
            )
            seance, _ = SeanceCours.objects.get_or_create(
                horaire=horaire,
                cours=cours,
                classe=classe,
                annee_academique=annee,
                date=d,
                defaults={"type": "cours"},
            )
            if self.skip_existing and Presence.objects.filter(eleve=eleve, seance=seance).exists():
                continue
            Presence.objects.update_or_create(
                eleve=eleve,
                seance=seance,
                defaults={"statut": r.get("statut") or "present"},
            )

    def _import_compte_eleve(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-compte-eleve.csv"], strict):
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            user = self._get_user(r.get("student_username"), strict)
            if not (annee and user):
                self._error("CompteEleve: references manquantes", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour compte", strict)
                continue
            if self.skip_existing and CompteEleve.objects.filter(eleve=eleve, annee_academique=annee).exists():
                continue
            CompteEleve.objects.update_or_create(
                eleve=eleve,
                annee_academique=annee,
                defaults={
                    "total_du": self._parse_decimal(r.get("total_du"), "total_du", strict) or 0,
                    "total_paye": self._parse_decimal(r.get("total_paye"), "total_paye", strict) or 0,
                },
            )

    def _import_payments(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-payments.csv"], strict):
                continue
            user = self._get_user(r.get("student_username"), strict)
            created_by = self._get_user(r.get("created_by_username"), strict)
            confirmed_by = self._get_user(r.get("confirmed_by_username"), strict) if r.get("confirmed_by_username") else None
            if not (user and created_by):
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour paiement", strict)
                continue
            if self.skip_existing and Paiement.objects.filter(reference=r.get("reference")).exists():
                continue
            Paiement.objects.update_or_create(
                reference=r.get("reference"),
                defaults={
                    "eleve": eleve,
                    "montant": self._parse_decimal(r.get("montant"), "montant", strict) or 0,
                    "mode": r.get("mode") or "CASH",
                    "statut": r.get("statut") or "PENDING",
                    "created_by": created_by,
                    "confirmed_by": confirmed_by,
                    "confirmed_at": self._parse_datetime(r.get("confirmed_at"), "confirmed_at", strict),
                },
            )

    def _import_paiement_allocations(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-paiement-allocations.csv"], strict):
                continue
            paiement = Paiement.objects.filter(reference=r.get("payment_reference")).first()
            user = self._get_user(r.get("student_username"), strict)
            if not (paiement and user):
                self._error("Allocation: references manquantes", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour allocation", strict)
                continue
            annee = AnneeAcademique.objects.filter(nom=r.get("annee_nom")).first()
            classe = Classe.objects.filter(nom=r.get("classe_code"), annee_academique=annee).first()
            frais = Frais.objects.filter(nom=r.get("frais_nom"), classe=classe, annee_academique=annee).first()
            if not frais:
                self._error("Frais introuvable pour allocation", strict)
                continue
            dette = DetteEleve.objects.filter(eleve=eleve, frais=frais).first()
            if not dette:
                self._error("Dette introuvable pour allocation", strict)
                continue
            if self.skip_existing and PaiementAllocation.objects.filter(paiement=paiement, dette=dette).exists():
                continue
            montant = self._parse_decimal(r.get("montant"), "montant", strict) or 0
            PaiementAllocation.objects.create(
                paiement=paiement,
                dette=dette,
                montant=montant,
            )
            dette.montant_paye += montant
            dette.montant_du = max(Decimal("0"), dette.montant_reduit - dette.montant_paye)
            dette.statut = "PAYE" if dette.montant_du == 0 else "PARTIEL"
            dette.save()

    def _import_invoices(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-invoices.csv"], strict):
                continue
            paiement = Paiement.objects.filter(reference=r.get("payment_reference")).first()
            user = self._get_user(r.get("student_username"), strict)
            if not (paiement and user):
                self._error("Facture: references manquantes", strict)
                continue
            eleve = Eleve.objects.filter(user=user).first()
            if not eleve:
                self._error("Eleve introuvable pour facture", strict)
                continue
            if self.skip_existing and Facture.objects.filter(numero=r.get("numero")).exists():
                continue
            Facture.objects.update_or_create(
                numero=r.get("numero"),
                defaults={
                    "paiement": paiement,
                    "eleve": eleve,
                    "montant": self._parse_decimal(r.get("montant"), "montant", strict) or 0,
                    "date_emission": self._parse_datetime(r.get("date_emission"), "date_emission", strict),
                    "statut": r.get("statut") or "PAID",
                },
            )

    def _import_notifications(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-notifications.csv"], strict):
                continue
            notif, _ = Notification.objects.get_or_create(
                titre=r.get("titre") or "",
                message=r.get("message") or "",
                defaults={
                    "type": r.get("type") or "info",
                },
            )
            self.notif_by_id[r.get("notification_id")] = notif

    def _import_notification_users(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-notification-users.csv"], strict):
                continue
            notif = self.notif_by_id.get(r.get("notification_id"))
            user = self._get_user(r.get("username"), strict)
            if not (notif and user):
                self._error("NotificationUser: references manquantes", strict)
                continue
            if self.skip_existing and NotificationUser.objects.filter(notification=notif, user=user).exists():
                continue
            NotificationUser.objects.update_or_create(
                notification=notif,
                user=user,
                defaults={
                    "is_read": self._bool(r.get("is_read")),
                    "read_at": self._parse_datetime(r.get("read_at"), "read_at", strict),
                },
            )

    def _import_notification_deliveries(self, rows, strict):
        for r in rows:
            if not self._require_fields(r, REQUIRED_COLUMNS["seed-notification-deliveries.csv"], strict):
                continue
            notif = self.notif_by_id.get(r.get("notification_id"))
            user = self._get_user(r.get("username"), strict)
            if not (notif and user):
                self._error("NotificationDelivery: references manquantes", strict)
                continue
            notif_user = NotificationUser.objects.filter(notification=notif, user=user).first()
            if not notif_user:
                self._error("NotificationUser introuvable pour delivery", strict)
                continue
            if self.skip_existing and NotificationDelivery.objects.filter(notification_user=notif_user, canal=r.get("canal") or "web").exists():
                continue
            NotificationDelivery.objects.create(
                notification_user=notif_user,
                canal=r.get("canal") or "web",
                status=r.get("status") or "sent",
                error_message=r.get("error_message") or "",
                sent_at=self._parse_datetime(r.get("sent_at"), "sent_at", strict),
            )

    def _skip_roles(self, rows, strict):
        self.stdout.write(self.style.WARNING("seed-roles.csv ignore (roles derives des profils)."))

    def _skip_chat(self, rows, strict):
        self.stdout.write(self.style.WARNING("seed-chat.csv ignore (modeles chat non presents)."))

    def _skip_audit(self, rows, strict):
        self.stdout.write(self.style.WARNING("seed-audit.csv ignore (modeles audit non presents)."))
