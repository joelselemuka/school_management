from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.db import transaction

class UserQuerySet(models.QuerySet):

    def with_profiles(self):

        return self.select_related(

            "eleve_profile",

            "parent_profile",

            "personnel_profile"

        )


class UserManager(BaseUserManager):
    
    @transaction.atomic
    def create_user(self, username, matricule, password=None, **extra_fields):

        if not username:
            raise ValueError("username obligatoire")

        if not matricule:
            raise ValueError("matricule obligatoire")

        user = self.model(
            username=username,
            matricule=matricule,
            **extra_fields
        )

        user.set_password(password)

        user.full_clean()

        user.save()

        return user

    def create_superuser(self, username, matricule=None, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("must_change_password", False)

        return self.create_user(
            username=username,
            matricule=matricule,
            password=password,
            **extra_fields
        )
    
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def with_profiles(self):
        return self.get_queryset().with_profiles()
 


# class ParentQuerySet(models.QuerySet):

#     def with_user(self):

#         return self.select_related("user")


class ParentManager(models.Manager):

    def get_queryset(self):

        return ParentQuerySet(self.model, using=self._db)


    def with_user(self):

        return self.get_queryset().with_user()


class UserRelatedQuerySet(models.QuerySet):

    def with_user(self):

        return self.select_related("user")


class ParentQuerySet(UserRelatedQuerySet):

    def active(self):

        return self.filter(user__is_active=True)


class PersonnelQuerySet(UserRelatedQuerySet):

    def active(self):

        return self.filter(user__is_active=True)


    def enseignants(self):

        return self.filter(fonction="enseignant")


    def administratifs(self):

        return self.exclude(fonction="enseignant")


class EleveQuerySet(UserRelatedQuerySet):

    def active(self):

        return self.filter(user__is_active=True)


    def with_parents(self):

        return self.prefetch_related("parenteleve_set__parent__user")


    def with_inscriptions(self):

        return self.prefetch_related("inscriptions")

    

