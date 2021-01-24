from flask import render_template, url_for, flash, redirect, request, Blueprint, jsonify, abort
from flask_login import login_user, current_user, logout_user, login_required
from qrave import db, bcrypt
from ..models import Users, Tickets, Events, Payments, TicketMeta
from ..users.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                                   RequestResetForm, ResetPasswordForm, TransferTicketForm, SellTicketForm, BuyTicketForm, TicketForm, BuyReservedTicketForm)
from ..users.utils import save_picture, send_reset_email, send_verify_email, send_purchase_email
from functools import wraps
import datetime
from ..swish import swish
import json
from sqlalchemy.sql.expression import not_

users = Blueprint('users', __name__)


@users.route("/register/", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    liuid = ""
    if form.validate_on_submit():
        print(form.liuid.data)
        if form.liuid.data.strip() == "":
            liuid = None 
        else:
            liuid = form.liuid.data
        user = Users(name=form.name.data, email=form.email.data, phone=form.phone.data, liuid=liuid)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        send_verify_email(user)
        flash('Ditt konto är skapat! Innan du kan logga in måste du verifiera ditt konto. Detta gör du genom att klicka på länken i det mejl vi skickat till den mejladress du angav.', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/register.html', title='Registrera konto', form=form)


@users.route("/login/", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data) and user.is_verified :
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Inloggningen lyckades!', 'success')
            if user.is_admin():
                return redirect(url_for('main.home'))
            return redirect(next_page) if next_page else redirect(url_for('users.tickets'))
        elif user and bcrypt.check_password_hash(user.password, form.password.data):
            flash('Du måste verifiera ditt konto innan du kan logga in!', 'danger')
        else :
            flash('Inloggningen lyckades inte. Dubbelkolla ditt lösenord och mailadress!', 'danger')
    return render_template('users/login.html', title='Logga in', form=form)


@users.route("/logout/")
def logout():
    logout_user()
    flash('Du är utloggad!', 'success')
    return redirect(url_for('main.home'))


@users.route("/account/", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone = form.phone.data
        current_user.liuid = form.liuid.data
        if not current_user.email == form.email.data:
            current_user.email = form.email.data
            send_verify_email(current_user)
            current_user.set_is_verified(False)
            logout_user()
            flash('Eftersom du uppdaterade din mejladress så måste du verifiera din nya mejladress. Det har skickat ett mejl till den nya mejladressen du angav.', 'info')
        else :
            current_user.email = form.email.data
        db.session.commit()
        flash('Ditt konto är uppdaterat!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.liuid.data = current_user.liuid
    return render_template('users/account.html', title='Konto', form=form)


@users.route("/reset_password/", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Ett mail har skickats till ditt konto med instruktioner för att återställa ditt lösenord.', 'info')
        return redirect(url_for('users.login'))
    return render_template('users/reset_request.html', title='Återställ lösenord', form=form)


@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = Users.verify_token(token)
    if user is None:
        flash('Din token har utgått eller så är den felaktig.', 'warning')
        return redirect(url_for('users.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Ditt lösenord är uppdaterat! Du kan nu logga in.', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/reset_token.html', title='Återställ lösenord', form=form)

@users.route("/verify_account/<token>", methods=['GET', 'POST'])
def verify_account(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = Users.verify_token(token)
    if user is None:
        flash('Din token har utgått eller så är den felaktig.', 'warning')
        return redirect(url_for('users.register'))
    if user:
        user.set_is_verified(True)
        db.session.commit()
        flash('Ditt konto är verifierat! Du kan nu logga in.', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/verify_account.html', title='Verifiera konto')

  
@users.route("/api/validatepassword/", methods=['POST'])
def validate_password():

    user = Users.query.filter_by(id=current_user.get_id()).first()
    
    if (bcrypt.check_password_hash(user.password, request.get_json().get('pwd'))):
        return jsonify(True, "Success")
    else: 
        return jsonify(False, "Wrong password")
 
@users.route("/tickets/", methods=['GET', 'POST'])
def tickets():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    
    for ticket in current_user.tickets:
        ticket.check_expired()
    
    tickets = Tickets.query.filter_by(owner=current_user, date_for_sale=None, reserved_by_id=None, used=False).join(Tickets.meta).order_by(TicketMeta.date_start.asc()).all()
    for ticket in tickets:
        p = Payments.query.filter(Payments.user_id==ticket.owner.id, Payments.tickets.any(id=ticket.id)).first()
        if p is not None:
            if p.swish_url is None:
                ticket.can_sell = False
            else:
                ticket.can_sell = True
        else:
            ticket.can_sell = False

    return render_template('users/tickets.html', title='Biljetter', ticket_sidenav=True, tickets=tickets)

@users.route("/reservedtickets/", methods=['GET', 'POST'])
def reservedtickets():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    
    for ticket in current_user.tickets:
        ticket.check_expired()

    class Ticket:
        meta = None
        available = None
    
    form = BuyReservedTicketForm()
    
    tickets_list = []
    reserved_dict = dict()
    reserved_list = []
    tickets = dict()

    if current_user.reserved_tickets:
        tickets_list = Tickets.query.filter_by(owner=None, date_for_sale=None, reserved_by_id=current_user.id, used=False).join(Tickets.meta).order_by(TicketMeta.date_start.asc())
        
        for ticket in tickets_list:
            if ticket.meta not in reserved_dict:
                reserved_dict[ticket.meta] = 1
            else:
                reserved_dict[ticket.meta] += 1
        reserved_list = [ [k,v] for k, v in reserved_dict.items() ] 

        for meta in reserved_list:
            ticket = Ticket()
            ticket.meta = meta[0]
            ticket.available = meta[1]
            tickets[meta[0].id] = ticket

        if request.method == 'POST':
            tot_price = 0
            for t in form.tickets:
                ticket = t.form
                tot_price += tickets[int(t.meta_id.data)].meta.price * ticket.amount.data
            
            r = swish.payment_request(form.phone.data, tot_price, 'Förköp')
            
            if len(r.content) > 0:
                err = list(form.phone.errors)
                err.append('Kontrollera Swishnummer. Kunde inte skapa betalningsbegäran.')
                form.phone.errors = tuple(err)
                return render_template('users/reservedtickets.html', title='Förköp', reserved_list=reserved_list, tickets=tickets, form=form, ticket_sidenav=True)
        
            if r.status_code == 201:
                payment = Payments(swish_url=r.headers['Location'], price=tot_price, user_id=current_user.id)
                for f in form.tickets:
                    t = tickets_list.filter(TicketMeta.id==f.meta_id.data).limit(f.amount.data)
                    if t is not None:
                        for ap in t:
                            payment.tickets.append(ap)
                    else:
                        swish.cancel_payment_request(r.headers['Location'])
                        flash('Biljetterna kunde inte reserveras', 'danger')
                        return render_template('users/reservedtickets.html', title='Förköp', reserved_list=reserved_list, tickets=tickets, form=form, ticket_sidenav=True)

                db.session.add(payment)
                db.session.commit()
                return redirect('/users/swish/' + str(payment.id))
        
        if request.method == 'GET':
            form.phone.data = current_user.phone
            for meta in reserved_list:
                t = TicketForm()
                t.meta_id = meta[0].id
                t.amount = 0
                form.tickets.append_entry(t)

    return render_template('users/reservedtickets.html', title='Förköp', reserved_list=reserved_list, tickets=tickets, form=form, ticket_sidenav=True)

@users.route("/usedtickets/", methods=['GET', 'POST'])
def usedtickets():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    
    for ticket in current_user.tickets:
        ticket.check_expired()

    tickets = Tickets.query.filter_by(owner=current_user, used=True).join(Tickets.meta).order_by(TicketMeta.date_start.asc()).all()

    return render_template('users/usedtickets.html', title='Biljetter', ticket_sidenav=True, tickets=tickets)

@users.route("/forsale_tickets/", methods=['GET', 'POST'])
def forsaletickets():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    
    for ticket in current_user.tickets:
        ticket.check_expired()
    
    tickets = Tickets.query.filter_by(owner_id=current_user.id, used=False, reserved_by=None).filter(Tickets.date_for_sale!=None).join(Tickets.meta).order_by(TicketMeta.date_start.asc()).all()

    return render_template('users/forsale_tickets.html', title='Biljetter', ticket_sidenav=True, tickets=tickets)


@users.route('/api/transferticket/', methods=['POST'])
def transferTicket():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/tickets/' ))
    
    receiving_user = Users.query.filter_by(id=request.form['uid']).first()
    ticket = Tickets.query.filter_by(id=int(request.form['id'])).first()
    
    if current_user.id != ticket.owner.id:
        abort(405)

    if ticket.date_for_sale != None or ticket.reserved_by_id != None:
        abort(406)

    ticket.transfer_ticket(receiving_user.id)
    flash('Din biljett är nu överförd till mailen du angav.', 'info')

    return jsonify(True)

@users.route("/api/validateticketform/", methods=['POST'])
def validateTicketForm():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/tickets/'))
   
    user = Users.query.filter_by(id=request.form['uid']).first()

    if user is None:
        return jsonify(False, user.email)
    else:
        return jsonify(True, user.email)

@users.route('/api/sellticket/', methods=['POST'])
def sellTicket():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/tickets/'))
    
    ticket = Tickets.query.filter_by(id=int(request.form['id'])).first()

    if current_user.id != ticket.owner.id:
        abort(405)

    if ticket.date_for_sale != None or ticket.reserved_by_id != None or ticket.used:
        abort(406)

    p = Payments.query.filter(Payments.user_id==ticket.owner.id, Payments.tickets.any(id=ticket.id)).first()
    if p.swish_url is None:
        abort(406)

    ticket.date_for_sale = datetime.datetime.now()
    db.session.commit()

    flash('Din biljett är nu upplagd för försäljning.', 'info')

    return jsonify(True)

@users.route('/api/undoticketsale/', methods=['POST'])
def undoticketsale():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/tickets/' ))
    
    ticket = Tickets.query.filter_by(id=int(request.form['id'])).first()

    if current_user.id != ticket.owner.id:
        abort(405)

    if ticket.date_for_sale == None or ticket.reserved_by_id != None or ticket.used:
        abort(406)

    ticket.date_for_sale = None
    db.session.commit()

    flash('Din biljett är nu borttagen för försäljning.', 'info')
    
    return jsonify(True)

@users.route('/buy_tickets/<int:event_id>', methods=['GET', 'POST'])
def buyTickets(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/buy_tickets/' + str(event_id)))

    event = Events.query.get(event_id)

    today = datetime.datetime.now()

    if event.date_ticket_sale > today:
        return render_template('users/buy_tickets.html', title='Köp biljetter', event=event, date=event.date_ticket_sale)

    class Ticket:
        meta = None
        available = None
    
    tickets = dict()
    form = BuyTicketForm()
    
    for meta in event.ticket_meta:
        if not meta.digital_release or (meta.digital_release and meta.date_ticket_release > datetime.datetime.now()):
            ticket = Ticket()
            ticket.meta = meta
            ticket.available = meta.get_second_hand_tickets().count() + meta.get_first_hand_tickets().count()
            tickets[meta.id] = ticket

    if request.method == 'POST':
        tot_price = 0
        for t in form.tickets:
            ticket = t.form
            tot_price += tickets[int(t.meta_id.data)].meta.price * ticket.amount.data
        
        r = swish.payment_request(form.phone.data, tot_price, "QRave - " + event.date_start.strftime('%Y-%m-%d'))
        #r = swish.payment_request(form.phone.data, tot_price, "RF07")
        if len(r.content) > 0:
            err = list(form.phone.errors)
            err.append('Kontrollera Swishnummer. Kunde inte skapa betalningsbegäran.')
            form.phone.errors = tuple(err)
            return render_template('users/buy_tickets.html', title='Köp biljetter', tickets=tickets, form=form, event=event)
        
        if r.status_code == 201:
            payment = Payments(swish_url=r.headers['Location'], price=tot_price, user_id=current_user.id)
            for f in form.tickets:
                for i in range(f.amount.data):
                    t = tickets[int(f.meta_id.data)].meta.get_first_hand_tickets().first()
                    if t is not None:
                        payment.tickets.append(t)
                        t.reserve_ticket(current_user.id, commit=False)
                    else:
                        t = tickets[int(f.meta_id.data)].meta.get_second_hand_tickets().first()
                        if t is not None and t.owner.id != current_user.id:
                            payment.tickets.append(t)
                            t.reserve_ticket(current_user.id, commit=False)
                        else:
                            swish.cancel_payment_request(r.headers['Location'])
                            flash('Biljetterna kunde inte reserveras', 'danger')
                            return render_template('users/buy_tickets.html', title='Köp biljetter', tickets=tickets, form=form, event=event)

            db.session.add(payment)
            db.session.commit()
            return redirect('/users/swish/' + str(payment.id))

    if request.method == 'GET':
        form.phone.data = current_user.phone
        for meta in event.ticket_meta:
            t = TicketForm()
            t.meta_id = meta.id
            t.amount = 0
            form.tickets.append_entry(t)

    return render_template('users/buy_tickets.html', title='Köp biljetter', tickets=tickets, form=form, event=event)


@users.route('/users/swish/<int:payment_id>', methods=['GET', 'POST'])
def userswish(payment_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/events/'))
    
    payment = Payments.query.get(payment_id)
    if not payment:
        return redirect('/events')

    if payment.user_id != current_user.id:
        return redirect(url_for('main.events'))

    if request.method == 'POST' and not payment.paid:
        phone = request.form['phone']
        message = request.form['message']
        r = swish.payment_request(phone, payment.price, message)
        payment.swish_url = r.headers['Location']
        db.session.commit()
        return redirect('/users/swish/' + str(payment.id))
    
    if request.method == 'GET' and not payment.paid:
        r = swish.payment_check(payment.swish_url)
        resp = json.loads(r.content)         
        if resp['status'] != 'CREATED' and resp['status'] != 'PAID':
            p = json.loads(swish.payment_check(payment.swish_url).content)
            phone = p['payerAlias']
            message = "Event"
            return render_template('users/swish.html', payment=payment, payment_failed=True, phone=phone, message=message)

    return render_template('users/swish.html', payment=payment, payment_failed=False)


@users.route('/api/swishForce', methods=['POST'])
def swishForce():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login'))
    
    url = request.environ['HTTP_SWISHURL']
    payment = Payments.query.filter_by(swish_url=url).first()
    user = Users.query.get(payment.user_id)
    if payment.paid:
        data = {'user': user.name}
        return jsonify(data)
    
    r = swish.payment_check(url)
    resp = json.loads(r.content)
    if resp['status'] == "PAID":
        second_hand_users = dict()
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
        send_purchase_email(user,payment)
        db.session.commit()
        return jsonify(resp)
    else:
        return jsonify(resp)
