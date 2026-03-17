from django.urls import path

from . import views


urlpatterns = (
    path('', views.DashBoard.as_view(), name='dashboard'),
    path('authenlist/', views.ProxmoxAuthList.as_view(), name='auth_list'),
    path('authenlist/<str:cluster>/', views.ProxmoxAuthEdit.as_view(), name='auth_edit'),
    path('authenlist/<str:cluster>/delete/', views.ProxmoxAuthDelete.as_view(), name='auth_delete'),
    path('get-nodes/<str:cluster>/', views.get_nodes, name='get_nodes') 




)
