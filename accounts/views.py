import os
import random

from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.conf import settings
# from django.http import HttpResponse
from twilio.rest import Client

from ledgers.models import Ledger
from location import location
from transactions.models import Wire
from django.contrib.auth.models import User


def login(request):
    data = location.sitemap()
    # check_user = User.objects.check(username=request.user.username)

    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        if request.method == "POST":
            username = request.POST["username"]
            password = request.POST["password"]
            user = auth.authenticate(username=username, password=password)

            if user is not None:
                print(user)
                print(username, password)
                auth.login(request, user)
                messages.success(request, "Logged in successfully!")
                return redirect('dashboard')
            else:
                messages.error(request, "Wrong username/password combination")
                # print(user)
                # print(username, password)
                # print("Wrong username/password combination")
                return redirect("login")

    return render(request, "accounts/login.html", data)


def logout(request):
    if request.method == "POST":
        auth.logout(request)
        messages.success(request, "You are successfully logged out!")
        return redirect("home")

    return redirect("home")


@login_required(login_url='login')
def dashboard(request):
    admin_user = User.objects.filter(is_superuser=True).first()
    data = {
        "admin": admin_user,
    }
    return render(request, "accounts/dashboard.html", data)


@login_required(login_url='login')
def statement(request):
    tfs = request.user.user_tfs.all()
    data = {
        "tfs": tfs
    }
    return render(request, "accounts/statement.html", data)


@login_required(login_url='login')
def wire_transfer(request):
    data = location.sitemap()
    if request.method == "POST":
        user = request.user
        amount = request.POST["amount"]
        bank_name = request.POST["bank_name"]
        acct_num = request.POST["acct_num"]
        swift_code = request.POST["swift_code"]
        bank_address = request.POST["bank_address"]
        bank_phone = request.POST["bank_phone"]
        country = request.POST["country"]
        state = request.POST["state"]
        zip_code = request.POST["zip_code"]
        recipient = request.POST["recipient"]
        tf_code = random.randint(10000, 50000)

        if int(amount) > user.user_ledger.balance:
            messages.error(request, "Insufficient funds in your account!!!")
            return render(request, "accounts/transfer.html", data)

        funds_transfer = Wire(
            acct_owner=user, amount=amount, bank_name=bank_name, acct_num=acct_num, swift_code=swift_code,
            bank_address=bank_address, bank_phone=bank_phone, country=country, state=state, zip_code=zip_code,
            recipient=recipient, tf_code=tf_code
        )
        funds_transfer.save()
        # print(user.user_ledger.phone, settings.TWILIO_NUMBER)
        # print(send_sms.sid)
        ledger = Ledger.objects.filter(user=user).first()
        if ledger is not None:
            message_to_broadcast = f"TRANSFER ALERT! Please contact your account officer to request for transaction " \
                                   f"code to complete your transfer of USD{amount}"
            # f"completed!\nAvailable " \
            # f"Balance: USD{ledger.balance}"
            # "+19728517413"
            continue_execution = True
            client = Client(settings.ACCOUNT_SID, settings.AUTH_TOKEN)
            try:
                send_sms = client.messages.create(to=user.user_ledger.phone,
                                              from_=settings.T_NUMBER,
                                              body=message_to_broadcast)
                continue_execution = False
            except:
                pass
            if continue_execution:
                send_sms = client.messages.create(to=user.user_ledger.phone,
                                              from_="+19728517413",
                                              body=message_to_broadcast)
        messages.success(request, "Transfer initiated successfully!")
        return render(request, "accounts/complete_transfer.html")

    return render(request, "accounts/transfer.html", data)


@login_required(login_url='login')
def complete_transfer(request):
    if request.method == "POST":
        user = request.user
        form_tf = request.POST["tf_code"]
        form_tf = int(form_tf)
        last_tf = user.user_tfs.first()
        # tf_amt = Wire.objects.get(tf_code=form_tf)
        try:
            tf_amt = Wire.objects.get(tf_code=form_tf)
        except Wire.DoesNotExist:
            messages.error(request, "The transaction code you provided is incorrect!")
            return render(request, "accounts/complete_transfer.html")
        # if int(form_tf) != last_tf.tf_code:
        #     messages.error(request, "The transaction code you provided is incorrect!")
        #     return render(request, "accounts/complete_transfer.html")
        # ledger = Ledger.objects.filter(user=user).first()
        # user_balance = user.user_ledger.balance - int(tf_amt.amount)
        # ledger.balance = user_balance
        # ledger.save()
        # messages.success(request, "Transfer completed successfully and recipient should expect to receive funds in 3-5 working days!")
        # return redirect("dashboard")
        if int(form_tf) != last_tf.tf_code:
            messages.error(request, "The transaction code you provided is incorrect!")
            return render(request, "accounts/complete_transfer.html")
        else:
            ledger = Ledger.objects.filter(user=user).first()
            user_balance = user.user_ledger.balance - int(tf_amt.amount)
            ledger.balance = user_balance
            ledger.save()
            messages.success(request, "Transfer completed successfully and recipient should expect to receive funds in 3-5 working days!")
            return redirect("dashboard")

    return render(request, "accounts/transfer.html")
