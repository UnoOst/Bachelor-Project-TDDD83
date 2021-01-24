from qrave import db
from flask import current_app
import requests
from ..models import Payments
import json

headers = {'Content-Type': 'application/json'}

def payment_request(phone, price, message):
    swish_cert = (current_app.root_path+'/swish/swish.pem', current_app.root_path+'/swish/swish.key')
    url = "https://mss.cpc.getswish.net/swish-cpcapi/api/v1/paymentrequests"
    payload = f'{{"payeePaymentReference": "0123456789", "callbackUrl": "https://qrave.herokuapp.com/api/swishcb/paymentrequests", "payerAlias": "{phone}","payeeAlias": "1234679304","amount": "{price}", "currency": "SEK", "message": "{message[0:48]}"}}'
    r = requests.post(url, data=payload.encode('utf-8'), cert=swish_cert, headers=headers, verify=False)
    return r


def refund_request(payment: Payments, amount):
    swish_cert = (current_app.root_path+'/swish/swish.pem', current_app.root_path+'/swish/swish.key')
    originalPaymentReference = json.loads(payment_check(payment.swish_url).content)['paymentReference']
    url = 'https://mss.cpc.getswish.net/swish-cpcapi/api/v1/refunds/'
    payload = f'{{"originalPaymentReference": "{originalPaymentReference}", "callbackUrl": "https://qrave.herokuapp.com/api/swishcb/refundrequests", "payerAlias": "1234679304" ,"amount": "{amount}", "currency": "SEK"}}'
    r = requests.post(url, data=payload.encode('utf-8'), cert=swish_cert, headers=headers, verify=False)
    return r


def payment_check(url):
    swish_cert = (current_app.root_path+'/swish/swish.pem', current_app.root_path+'/swish/swish.key')
    r = requests.get(url, cert=swish_cert, headers=headers, verify=False)
    return r


def cancel_payment_request(url):
    swish_cert = (current_app.root_path+'/swish/swish.pem', current_app.root_path+'/swish/swish.key')
    headers2 = {'Content-Type':'application/json-patch+json'}
    payload = '[{“op”: “replace”, “path”: “/status”, “value”: “cancelled”}]'
    r = requests.patch(url, data=payload.encode('utf-8'), cert=swish_cert, headers=headers2, verify=False)