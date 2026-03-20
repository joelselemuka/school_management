from rest_framework import serializers

from academics.models import Evaluation,Note

from academics.services.note_service import NoteService
from users.models import Eleve



class NoteCreateSerializer(serializers.ModelSerializer):

    class Meta:

        model = Note

        fields = [
            "eleve",
            "evaluation",
            "valeur"
        ]
    def validate_valeur(self, value):

        evaluation = self.instance.evaluation if self.instance else self.initial_data.get("evaluation")

        if value > evaluation.bareme:

            raise serializers.ValidationError(
                "Note dépasse le barème"
            )

        return value


class NoteUpdateSerializer(serializers.Serializer):
    valeur = serializers.DecimalField(decimal_places=2, max_digits=5)
    



class NoteReadSerializer(serializers.ModelSerializer):


    eleve_nom = serializers.CharField(
        source="eleve.user.full_name",
        read_only=True
    )


    evaluation_nom = serializers.CharField(
        source="evaluation.nom",
        read_only=True
    )


    class Meta:

        model = Note

        fields = "__all__"