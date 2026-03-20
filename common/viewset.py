from rest_framework.viewsets import ModelViewSet

class SoftDeleteModelViewSet(ModelViewSet):
    def perform_destroy(self, instance):
        if hasattr(instance,"soft_delete"):
            instance.soft_delete()
        else:
            instance.delete()
