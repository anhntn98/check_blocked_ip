from django.urls import path

from . import views


urlpatterns = (
    path('', views.DashBoard.as_view(), name='dashboard'),
)
