from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^launch$', views.launch, name='launch'),
    url(r'^auth$', views.auth, name='auth'),
    url(r'^$', views.index, name='index'),
]