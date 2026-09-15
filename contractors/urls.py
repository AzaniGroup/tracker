from django.urls import path
from . import views

app_name='contractors'
urlpatterns = [
    path('', views.SubcontractorListView.as_view(), name='contractor_list'),
    path('add/', views.add_subcontractor, name='add_subcontractor'),
    path('edit/<int:pk>/', views.edit_subcontractor, name='edit_subcontractor'),
    path('delete/<int:pk>/', views.delete_subcontractor, name='delete_subcontractor'),
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/add/', views.add_company, name='add_company'),
    path('companies/edit/<int:pk>/', views.edit_company, name='edit_company'),
    path('companies/delete/<int:pk>/', views.delete_company, name='delete_company'),
    path('compliance/', views.ComplianceMatrixView.as_view(), name='compliance_matrix'),
    path('compliance/manage/', views.ManageComplianceView.as_view(), name='manage_compliance'),
    path('compliance/upload/', views.upload_compliance_document, name='upload_compliance_document'),
    path('compliance/requirements/', views.manage_compliance_requirements, name='manage_compliance_requirements'),
]   