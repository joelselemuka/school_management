"""
Views du module Academics.
"""

# Import depuis main_views.py
from .main_views import (
    ClasseViewSet,
    CoursViewSet,
    NoteViewSet,
    EvaluationViewSet,
    AffectationViewSet,
    BulletinViewSet
)

# Import depuis exam_views.py
from .exam_views import (
    SalleViewSet,
    SessionExamenViewSet,
    PlanificationExamenViewSet,
    RepartitionExamenViewSet,
    ExamDistributionViewSet
)

__all__ = [
    # ViewSets principaux
    'ClasseViewSet',
    'CoursViewSet',
    'NoteViewSet',
    'EvaluationViewSet',
    'AffectationViewSet',
    'BulletinViewSet',
    # ViewSets examens
    'SalleViewSet',
    'SessionExamenViewSet',
    'PlanificationExamenViewSet',
    'RepartitionExamenViewSet',
    'ExamDistributionViewSet',
]
