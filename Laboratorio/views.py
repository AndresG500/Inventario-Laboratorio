from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render


def home(request):
    return render(request, "Register.html", {"form_register": UserCreationForm()})


def login(request):
    return render(request, "Login.html", {"form_login": AuthenticationForm()})


# Create your views here.
