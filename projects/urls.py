from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('export/excel/', views.export_projects_excel, name='export_projects_excel'),
    path('activity-log/', views.ProjectActivityLogListView.as_view(), name='activity_log'),
    path('create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('settings/', views.ProjectSettingsView.as_view(), name='settings'),
    path('monitoring/', views.ProjectMonitoringDashboardView.as_view(), name='monitoring_dashboard'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('<int:pk>/expenses/', views.ProjectExpenseBreakdownView.as_view(), name='project_expense_breakdown'),
    path('<int:pk>/expenses/export/', views.export_project_expense_breakdown, name='export_project_expense_breakdown'),
    
    # Subcontractor Allocation routes
    path('<int:project_pk>/allocate/', views.ProjectAllocationCreateView.as_view(), name='allocation_create'),
    path('allocate/<int:pk>/update/', views.ProjectAllocationUpdateView.as_view(), name='allocation_update'),
    path('allocate/<int:pk>/delete/', views.ProjectAllocationDeleteView.as_view(), name='allocation_delete'),
    
    # Lifecycle Stage routes
    path('lifecycle/<int:pk>/update/', views.UpdateLifecycleStageView.as_view(), name='lifecycle_update'),
    
    # Progress Monitoring routes
    path('<int:project_pk>/monitoring/create/', views.ProjectMonitoringLogCreateView.as_view(), name='monitoring_log_create'),
    path('monitoring/log/<int:pk>/delete/', views.ProjectMonitoringLogDeleteView.as_view(), name='monitoring_log_delete'),
    path('monitoring/log/<int:pk>/add-images/', views.ProjectMonitoringImageAddView.as_view(), name='monitoring_log_add_images'),
    path('monitoring/image/<int:pk>/delete/', views.ProjectMonitoringImageDeleteView.as_view(), name='monitoring_image_delete'),
    
    # Subcontractor payment tranche routes
    path('allocate/<int:allocation_pk>/tranche/create/', views.SubcontractorPaymentTrancheCreateView.as_view(), name='subcontractor_tranche_create'),
    
    # Phase comment route
    path('<int:project_pk>/phase-comment/', views.AddPhaseCommentView.as_view(), name='add_phase_comment'),
]

