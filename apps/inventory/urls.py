from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Products
    path('', views.ProductListView.as_view(), name='list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='detail'),
    path('create/', views.ProductCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.ProductUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='delete'),
    path('api/product/<int:product_id>/price/', views.get_product_price, name='get_product_price'),

    # Item Groups
    path('groups/', views.ItemGroupListView.as_view(), name='group_list'),
    path('groups/create/', views.ItemGroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/update/', views.ItemGroupUpdateView.as_view(), name='group_update'),
    path('groups/<int:pk>/delete/', views.ItemGroupDeleteView.as_view(), name='group_delete'),
]
