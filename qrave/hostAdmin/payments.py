import json
import os
import time
from datetime import datetime
from functools import wraps

import bleach
import requests
from flask import (Blueprint, Response, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user
from sqlalchemy.sql.expression import not_, or_
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.utils import secure_filename

from qrave import db
from ..swish import swish as swp

from ..hostAdmin.forms import (CreateEventForm, EventForm, ProductForm,
                               UpdateAccountForm)
from ..models import Events, Hosts, Products, TicketMeta, Tickets, Users, Payments, Logs, LogText

payment_blueprint = Blueprint('payment', __name__)


@payment_blueprint.route("/hostAdmin/ticket_sale/<int:event_id>/")
def sale(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))
    event = Events.query.get(event_id)
        
    return render_template('hostAdmin/ticket_sale.html', title='Fysisk biljettförsäljning', event=event, host_sidenav=True, host=event.host)


def isEventHost(event_id):
    event = Events.query.get(event_id)
    hosts = [event.host.id]
    if event.cohosts:
        for cohost in event.cohosts:
            hosts.append(cohost.id)
    
    isHost = False
    for host in hosts:
        if current_user.is_host(host):
            isHost = True
            break
    
    return isHost


def formToDict(form):
    error = dict()
    items = dict()
    newForm = form.copy()
    for data in form:
        if 'ticket-' in data:
            if request.form[data] != "" and int(request.form[data]) > 0:
                ticket_meta_id = int(data[7:])
                ticket_meta = TicketMeta.query.get(ticket_meta_id)
                items[ticket_meta_id] = dict(ticket=ticket_meta, amount=int(request.form[data]))
                tickets_left = ticket_meta.unsold_tickets()
                if tickets_left < int(request.form[data]):
                    error[data] = 'Endast ' + str(tickets_left) + ' biljetter kvar.'
                elif int(request.form[data]) < 0:
                    error[data] = 'Antal biljetter får inte vara negativt.'
                elif ticket_meta.max_per_user < int(request.form[data]):
                    error[data] = 'Max ' + str(ticket_meta.max_per_user) + ' biljetter per person.'
    if len(items) == 0:
        for data in form:
            if 'ticket-' in data:
                    error[data] = 'Minst en biljett måste vara större än 0'
    newForm.add('tickets', items)
    return newForm, error
    

@payment_blueprint.route("/api/hostAdmin/validateticketform/<int:event_id>", methods=['POST'])
def validateTicketForm(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/ticket_sale/' + event_id))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))
    
    form, error = formToDict(request.form)
    user = Users.query.filter_by(id=request.form['uid']).first()
    if user is None:
        error['uid'] = 'Den användaren hittades inte.'
    
    if len(error) > 0:
        return jsonify(error)
    return jsonify(True)


@payment_blueprint.route('/api/hostAdmin/transfertickets/<int:event_id>', methods=['POST'])
def transferticket(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/ticket_sale/' + event_id))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))

    form, error = formToDict(request.form)
    user = Users.query.filter_by(id=request.form['uid']).first()
    
    if user is None:
        error['uid'] = 'Den användaren hittades inte.'
    if len(error) > 0:
        return jsonify(error)

    payment = Payments(price=form['price'], paid=True, user_id=user.id)

    for id in form['tickets']:
        for i in range(form['tickets'][id]['amount']):
            ticket = form['tickets'][id]['ticket'].get_first_free_ticket()
            if ticket is not None:
                ticket.transfer_ticket(user.id)
                payment.tickets.append(ticket)
            else:
                error[id] = 'Biljett ' + form['tickets'][id]['ticket'].name + ' kunde ej överföras till ' + user.name + '.'
    
    db.session.add(payment)
    db.session.commit()

    if len(error) > 0:
        return jsonify(error)
    return jsonify(True)


@payment_blueprint.route('/api/hostAdmin/swish/<int:event_id>', methods=['POST'])
def swish(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/ticket_sale/' + event_id))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))
    
    server_errors = dict()
    response = {'server_errors': server_errors, 'swish_errors': dict(), 'swish_url': ''}
    user = Users.query.get(request.form['uid'])
    
    event = Events.query.get(event_id)
    form, errors = formToDict(request.form)
    phone = str.strip(form['phone'])
    price = str.strip(form['price'])

    if len(errors) > 0:
        response['server_errors'] = errors
        return jsonify(response)
        
    message = 'QRave biljettköp - ' + str(event.date_start.date())
    r = swp.payment_request(phone, price, message)
    
    if len(r.content) > 0:
        resp = json.loads(r.content)
        response['swish_errors'] = resp[0]
        return jsonify(response)

    if r.status_code == 201:
        payment = Payments(swish_url=r.headers['Location'], price=price, user_id=user.id)
        response['swish_url'] = r.headers['Location']
        for id in form['tickets']:
            for n in range(form['tickets'][id]['amount']):
                t = TicketMeta.query.get(id).get_first_free_ticket()
                if t is not None:
                    payment.tickets.append(t)
                    t.reserve_ticket(user.id, commit=False)
                else:
                    errors[id] = f'Biljett {form.tickets[id].name} kunde inte reserveras.'
        if len(errors) > 0:
            response['server_errors'] = errors
            swp.cancel_payment_request(r.headers['Location'])
        else:
            db.session.add(payment)
            db.session.commit()
    
    return jsonify(response)


@payment_blueprint.route('/api/hostAdmin/swishForce', methods=['POST'])
def swishForce():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login'))
    
    url = request.environ['HTTP_SWISHURL']
    payment = Payments.query.filter_by(swish_url=url).first()
    user = Users.query.get(payment.user_id)
    if payment.paid:
        data = {'user': user.name}
        return jsonify(data)
    
    r = swp.payment_check(url)
    resp = json.loads(r.content)
    if resp['status'] == "PAID":
        payment.paid = True
        for ticket in payment.tickets:
            ticket.transfer_ticket(user.id)
        data = {'user': user.name}
        db.session.commit()
        return jsonify(data)
    else:
        return jsonify(resp)


@payment_blueprint.route('/api/swishcb/paymentrequests', methods=['POST'])
def swishcallback():
    if request.json['status'] == 'PAID':
        payment = Payments.query.filter(Payments.swish_url.contains(request.json['id'])).first()
        if payment:
            if not payment.paid:
                payment.paid = True
                
                for ticket in payment.tickets:
                    if ticket.owner is not None:
                        shup = Payments.query.filter(Payments.user_id==ticket.owner.id, Payments.tickets.any(id=ticket.id)).first()
                        if shup.id in second_hand_users:
                            second_hand_users[shup.id] += ticket.meta.price
                        else:
                            second_hand_users[shup.id] = ticket.meta.price
                
                for ticket in payment.tickets:
                    ticket.transfer_ticket(payment.user_id)
                for pid, amount in second_hand_users.items():
                    p = Payments.query.get(pid)
                    resp = swish.refund_request(p, amount)
                send_purchase_email(User.query.get(payment.user_id), payment)
                db.session.commit()
    return ""


@payment_blueprint.route('/api/getusers/')
def getusers():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login'))

    search = request.args.get('email')
    if search is not None:
        users = Users.query.filter(or_(Users.email.contains(search), Users.liuid.contains(search), Users.name.contains(search))).limit(100).all()
    else:
        users = Users.query.limit(10).all()
    arr = []
    results = {"results": arr}
    for u in users:
        user = {"id": u.id, "text": u.name + ": " + u.email}
        arr.append(user)
    
    return jsonify(results)


@payment_blueprint.route('/api/getphone/<int:uid>')
def getphone(uid):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login'))
    if not current_user.is_host():
        return redirect(url_for('main.home'))
    
    user = Users.query.get(uid)
    if user is not None:
        return jsonify(user.phone)
    return ""        


@payment_blueprint.route("/api/unsold_tickets/<int:event_id>")
def unsoldTickets(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))

    event = Events.query.get(event_id)
    unsoldtickets = dict()
    for ticket_meta in event.ticket_meta:
        unsoldtickets[ticket_meta.id] = dict(unsold=ticket_meta.unsold_tickets(), capacity=ticket_meta.capacity, reserved=ticket_meta.reserved_tickets())
    return jsonify(unsoldtickets)


@payment_blueprint.route("/api/sales_log/<int:event_id>", methods=['GET', 'POST'])
def get_log(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))

    log = Logs.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    
    if log is None:
        log = Logs(user_id=current_user.id, event_id=event_id)
        db.session.add(log)
        db.session.commit()

    if request.method == 'POST':
        text = LogText(text=request.form['log'])
        log.logs.append(text)
        db.session.commit()
        return jsonify(str(text.date.time().strftime('%H:%M')) + " " + request.form['log'])
    
    logs = LogText.query.filter_by(log_id=log.id).order_by(LogText.date.asc())
    return jsonify([(str(log.date.time().strftime('%H:%M')) + " " + log.text) for log in logs])
