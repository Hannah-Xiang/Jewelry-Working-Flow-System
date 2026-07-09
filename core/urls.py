from django.urls import path
from . import views

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
]