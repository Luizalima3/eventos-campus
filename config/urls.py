from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contas/', include('django.contrib.auth.urls')),
    path('api/', include('eventos.api.urls')),
    path('', include('eventos.urls')),
]
