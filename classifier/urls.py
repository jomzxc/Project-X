from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('history/', views.job_history_view, name='job_history'),
    path('notebook/', views.notebook_view, name='notebook'),
    path('results/<str:job_id>/', views.results_view, name='results'),
    path('delete_job/<str:job_id>/', views.delete_job_view, name='delete_job'),
    path('api/classify/', views.api_classify_single, name='api_classify_single'),
    path('download/<str:job_id>/', views.download_results_csv, name='download_csv'),
]
