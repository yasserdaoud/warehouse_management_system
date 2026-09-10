from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="includes/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(template_name="includes/logout.html"), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("stock/", views.view_stock, name="view_stock"),
    path("stock/add/", views.stock_create, name="stock_create"),
    path("stock/<int:pk>/", views.stock_detail, name="stock_detail"),
    path("stock/<int:pk>/edit/", views.stock_update, name="stock_update"),
    path("stock/<int:pk>/adjust/", views.stock_adjust, name="stock_adjust"),
    path("stock/<int:pk>/delete/", views.stock_delete, name="stock_delete"),
    path("items-in-service/", views.items_in_service, name="items_in_service"),
    path("history/", views.view_history, name="view_history"),
    path("contacts/", views.contacts, name="contacts"),
    path("contacts/add/", views.supplier_create, name="supplier_create"),
    path( "contacts/<int:pk>/edit/", views.supplier_update, name="supplier_update" ),
    path( "contacts/<int:pk>/delete/", views.supplier_delete, name="supplier_delete"),
    path("contacts/<int:pk>/", views.supplier_detail, name="supplier_detail",),
    path("contracts/", views.contracts, name="contracts"),
    path("contracts/add/", views.contract_create, name="contract_create"),
    path("contracts/<int:pk>/edit/", views.contract_update, name="contract_update"),
    path("contracts/<int:pk>/delete/", views.contract_delete, name="contract_delete"),
    path("contracts/<int:pk>/", views.contract_detail, name="contract_detail"),
]
