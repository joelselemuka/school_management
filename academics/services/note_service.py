from django.db import transaction
from academics.models import Note


class NoteService:


    @staticmethod
    def get(pk):

        return Note.objects.select_related(
            "eleve",
            "evaluation"
        ).get(pk=pk)


    @staticmethod
    @transaction.atomic
    def create(data):

        return Note.objects.create(**data)


    @staticmethod
    @transaction.atomic
    def update(pk, data):

        note = Note.objects.get(pk=pk)

        for attr, value in data.items():

            setattr(note, attr, value)

        note.save()

        return note


    @staticmethod
    @transaction.atomic
    def delete(pk):

        Note.objects.get(pk=pk).delete()