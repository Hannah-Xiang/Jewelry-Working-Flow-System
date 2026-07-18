from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('new-ticket/', views.new_ticket, name='new_ticket'),
    path('tickets/', views.all_tickets, name='all_tickets'),
    path(
        'tickets/search/',
        views.ticket_search,
        name='ticket_search'
    ),
    path(
        'ticket/<int:ticket_id>/',
        views.ticket_detail,
        name='ticket_detail'
    ),
    path('calendar/', views.calendar, name='calendar'),
    path('customers/', views.customers, name='customers'),

    path(
        'api/customers/search/',
        views.customer_search,
        name='customer_search'
    ),

    path(
        'api/customers/<int:pk>/',
        views.customer_detail,
        name='customer_detail_api'
    ),

    path(
        'api/jobtypes/<int:pk>/',
        views.jobtype_detail,
        name='jobtype_detail'
    ),

    path(
        'api/ticket-number/',
        views.generate_ticket,
        name='generate_ticket'
    ),

    path('ticket/<int:ticket_id>/edit/', views.edit_ticket, name='edit_ticket'),
    path('ticket/<int:ticket_id>/add-note/', views.add_note, name='add_note'),
    path('ticket/<int:ticket_id>/add-photo/', views.add_photo, name='add_photo'),
    path('ticket/<int:ticket_id>/set-status/<int:status_id>/', views.set_status, name='set_status'),
    path(
    "note/<int:note_id>/delete/",
    views.delete_note,
    name="delete_note",
    ),
    path(
    "notes/<int:note_id>/delete/",
    views.delete_note,
    name="delete_note",
),
]

# Media files (uploaded ticket photos) are only served this way in development.
# In production, your web server (nginx, etc.) or a storage backend (S3, etc.)
# should serve MEDIA_URL instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
