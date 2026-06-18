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
]