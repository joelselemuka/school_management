from bibliotheque.models import Livre

class LivreService:
    @staticmethod
    def create_livre(validated_data):
        return Livre.objects.create(**validated_data)

    @staticmethod
    def update_livre(livre, validated_data):
        for attr, value in validated_data.items():
            setattr(livre, attr, value)
        livre.save()
        return livre

    @staticmethod
    def get_all_actifs():
        return Livre.objects.filter(actif=True)
