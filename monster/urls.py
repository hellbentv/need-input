from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Home
    url(r'^$', 'puke.views.home', name='home'),

    # Handle JS libs and CSS.
    url(r'^js/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.JS_PATH}),
    url(r'^css/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.CSS_PATH}),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
