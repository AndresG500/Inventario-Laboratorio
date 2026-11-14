from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User


def singup(request):
    if request.method == 'GET':
        return render(request, "Register.html", {"form_register": UserCreationForm()})
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(username=request.POST['username'],
                password=request.POST['password1'])
                user.save()
                return HttpResponse('Usuario registrado')
            except:
                return render(request, "Register.html", {
                    "form_register": UserCreationForm,
                    "error": 'El usuario ya existe'
                })
        return render(request, "Register.html",{
                "form_register": UserCreationForm,
                "error": 'La contraseña no coincide'
        })

def login(request):
    return render(request, "Login.html", {"form_login": AuthenticationForm()})


# Create your views here.
