from django.db import transaction
import secrets

from common.role_services import User
from users.models import Eleve, Parent, ParentEleve


class ParentService:


    @staticmethod
    @transaction.atomic
    def create(data):


        username = data["username"]


        email = data.get("email")


        if email and User.objects.filter(email=email).exists():

            raise ValueError("Email déjà utilisé")


        password = data.get("password")

        if not password:

            password = secrets.token_urlsafe(10)


        user = User.objects.create_user(

            username=username,

            email=email,

            password=password

        )


        parent = Parent.objects.create(

            user=user,

            nom=data["nom"],

            postnom=data["postnom"],

            prenom=data["prenom"],

            telephone=data["telephone"],

            adresse=data["adresse"],
            sexe=data["sexe"]

        )


        return parent, password
    
    
    @staticmethod
    @transaction.atomic
    def add_student(parent_id, eleve_id, reduction_percent=0):


        parent = Parent.objects.get(id=parent_id)

        eleve = Eleve.objects.get(id=eleve_id)


        relation, created = ParentEleve.objects.get_or_create(

            parent=parent,

            eleve=eleve,

            defaults={

                "reduction_percent": reduction_percent

            }

        )


        if not created:

            relation.reduction_percent = reduction_percent

            relation.save()


        return relation
    
    
    @staticmethod
    @transaction.atomic
    def update(parent_id, data):

        parent = Parent.objects.select_related("user").get(id=parent_id)

        user = parent.user


        parent.nom = data.get("nom", parent.nom)

        parent.postnom = data.get("postnom", parent.postnom)

        parent.prenom = data.get("prenom", parent.prenom)

        parent.telephone = data.get("telephone", parent.telephone)

        parent.adresse = data.get("adresse", parent.adresse)
        parent.sexe = data.get("adresse", parent.sexe)

        parent.save()


        email = data.get("email")

        if email:

            user.email = email

            user.save()


        return parent
    
    @staticmethod
    @transaction.atomic
    def delete(parent_id):

        parent = Parent.objects.select_related("user").get(id=parent_id)

        parent.delete()

        parent.user.is_active = False

        parent.user.save()
    
    
    
    
    