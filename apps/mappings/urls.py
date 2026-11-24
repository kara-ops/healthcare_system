from django.urls import path
from . import views

# NOTE: GET and DELETE on mappings/<int:pk>/ have DIFFERENT semantics:
# - GET treats pk as a patient_id (list doctors for that patient)
# - DELETE treats pk as a mapping_id (remove that specific mapping)
# This is by spec design. See API_CONTRACT.md section 4.
urlpatterns = [
    path('', views.MappingListCreateView.as_view(), name='mapping-list-create'),
    path('<int:pk>/', views.MappingDetailView.as_view(), name='mapping-detail'),
]
