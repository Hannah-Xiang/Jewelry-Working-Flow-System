from django.shortcuts import render

# Create your views here.

def dashboard(request):
    return render(request, 'core/dashboard.html')

def new_ticket(request):
    return render(request, 'core/new_ticket.html')

def all_tickets(request):
    return render(request, 'core/all_tickets.html')

def calendar(request):
    return render(request, 'core/calendar.html')

def customers(request):
    return render(request, 'core/customers.html')

def base(request):
    return render(request, 'core/base.html')
