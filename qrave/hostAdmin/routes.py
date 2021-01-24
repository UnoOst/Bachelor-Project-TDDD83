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

from ..hostAdmin.forms import (CreateEventForm, EventForm, ProductForm,
                               UpdateAccountForm)
from ..models import Events, Hosts, Products, TicketMeta, Tickets, Users

host_blueprint = Blueprint('host', __name__)

tags = bleach.sanitizer.ALLOWED_TAGS
tags.extend(('p', 'strike', 'span', 'sup', 'u', 'br', 'sub', 'div'))
attr = bleach.sanitizer.ALLOWED_ATTRIBUTES
attr['*'] = ['style']
styles = ['text-align']


@host_blueprint.route("/hostAdmin/create_event/<int:host_id>", methods=['GET', 'POST'])
def createEvent(host_id):
    host = Hosts.query.filter_by(id=host_id).first()
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    if not current_user.is_host(Hosts.query.filter_by(id=host_id).first().id):
        return redirect(url_for('main.home'))
    
    form = CreateEventForm(CombinedMultiDict((request.files, request.form)))
    form.event.form.cohosts.choices = [(h.id, h.short_name) for h in Hosts.query.filter(not_(Hosts.id.contains(host_id))).order_by('short_name')]
    if request.method == "GET":
        form.products.append_entry()

    if request.form.get('products') == "no":
        form.products.entries.clear()

    if form.validate_on_submit():
        # Säkrar beksrivningsinput
        form.event.form.description.data = bleach.clean(form.event.form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)
        for ticket in form.tickets:
            ticket.form.description.data = bleach.clean(ticket.form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)
        for product in form.products:
            product.form.description.data = bleach.clean(product.form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)

        # Event
        edata = form.event.form
        event = Events(
            name=edata.event_name.data,
            description=edata.description.data,
            date_start=edata.date_start.data,
            date_end=edata.date_end.data,
            date_publication=edata.date_publication.data,
            date_ticket_sale=edata.date_ticket_release.data,
            ticket_location=edata.location_tr.data,
            host_id=host_id)
        
        if edata.image.data:
            _, extension = os.path.splitext(edata.image.data.filename)
            filename = secure_filename(event.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
            edata.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
            event.image = 'images/uploads/' + filename

        for cohost_id in edata.cohosts.data:
            if cohost_id != host_id:
                cohost = Hosts.query.filter_by(id=cohost_id).first()
                if cohost:
                    event.cohosts.append(cohost)

        # Biljetter
        for ticket in form.tickets:
            newticket = TicketMeta(
                name=ticket.form.name.data,
                price=ticket.form.price.data,
                description=ticket.form.description.data,
                capacity=ticket.form.capacity.data,
                date_start=ticket.form.date_start.data,
                date_end=ticket.form.date_end.data,
                date_ticket_release=ticket.form.date_ticket_release_to_digital.data,
                location=ticket.form.location.data,
                digital_release=int(ticket.form.digital_release.data)
            )
            
            if newticket.digital_release:
                newticket.date_ticket_release = event.date_ticket_sale

            if ticket.form.max_per_user.data is None:
                newticket.max_per_user = capacity
            else:
                newticket.max_per_user = ticket.form.max_per_user.data

            if ticket.form.image.data:
                _, extension = os.path.splitext(ticket.form.image.data.filename)
                filename = secure_filename(event.name + newticket.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                ticket.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                newticket.image = 'images/uploads/' + filename

            event.ticket_meta.append(newticket)

        # Produkter
        if form.products and request.form.get('products') == "yes":
            for product in form.products:
                newproduct = Products(
                    name=product.form.name.data,
                    price=product.form.price.data,
                    capacity=product.form.capacity.data,
                    description=product.form.description.data
                )

                if product.form.image.data:
                    _, extension = os.path.splitext(product.form.image.data.filename)
                    filename = secure_filename(event.name + newproduct.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                    product.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                    newproduct.image = 'images/uploads/' + filename
                    
                event.products.append(newproduct)

        db.session.add(event)    
        db.session.commit()
        
        for ticket in event.ticket_meta:
            ticket.generate_tickets()
        
        flash('Eventet skapat!', 'success')
        return redirect('/events/')
    return render_template('hostAdmin/create_event.html', form=form, title='Skapa event', host=host, host_id=host_id, host_sidenav=True)


@host_blueprint.route("/api/hostAdmin/validate/<int:page>/", methods=['POST'])
def validateForm(page):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    if not current_user.is_host():
        return redirect(url_for('main.home'))

    form = CreateEventForm(CombinedMultiDict((request.files, request.form)))
    form.event.form.cohosts.choices = [(h.id, h.short_name) for h in Hosts.query.order_by('short_name')]
    if page == 1 and form.event.validate(form):
        return "1"
    if page == 2 and form.tickets.validate(form.tickets):
        return "2"
    if request.form.get('products') == 'yes':
        if page == 3 and form.products.validate(form):
            return "3"
    elif request.form.get('products') == 'no':
        return "3"
    if form.tickets.errors is not None and page == 2:
        errors = []
        for t in form.tickets:
            errors.append(t.errors)
        form.tickets.errors = errors
    return jsonify(data=form.errors)

def isEventHost(event_id):
    event = Events.query.get(event_id)
    hosts = [event.host.short_name]
    if event.cohosts:
        for cohost in event.cohost:
            hosts.append(cohost.short_name)
    
    isHost = False
    for host in hosts:
        if current_user.is_host(host):
            isHost = True
            break
    
    return isHost

@host_blueprint.route("/hostAdmin/edit_event/<int:event_id>/", methods=['GET', 'POST'])
def editEvent(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next=request.url))
    
    event = Events.query.get(event_id)
    if event is not None:
        if not isEventHost(event_id):
            return redirect(url_for('main.home'))
        
        host = event.host
        host_id = host.id
        form = CreateEventForm(CombinedMultiDict((request.files, request.form)))    
        form.event.form.cohosts.choices = [(h.id, h.short_name) for h in Hosts.query.filter(not_(Hosts.id.contains(host_id))).order_by('short_name')]
        
        if request.method == 'GET':
            form.event.insertOldValues(event)
            
            count = 0
            products_img = dict()
            for i in event.products:
                form.products.append_entry(i)
                form.products[count].insertOldValues(i)
                products_img[count] = i.image
                count += 1
            
            count = 0
            tickets_img = dict()
            for i in event.ticket_meta:
                if (count != 0):
                    form.tickets.append_entry(i)
                form.tickets[count].insertOldValues(i)
                tickets_img[i.id] = i.image
                count += 1
            
            form.event.form.cohosts.data = [h.id for h in event.cohosts]
            form.products.append_entry()
            
            return render_template('hostAdmin/edit_event.html', title='Ändra event', form=form, host_id=host_id, nrOfProducts=len(event.products), event=event, host_sidenav=True, host=host, tickets_img=tickets_img, products_img=products_img)
        
        if request.form.get('products') == "no":
            form.products.entries.clear()
            for i in event.products:
                db.session.delete(i)

        if form.validate_on_submit():
            form.event.description = bleach.clean(form.event.description, tags=tags, attributes=attr, styles=styles)
            for ticket in form.tickets:
                ticket.description = bleach.clean(ticket.description, tags=tags, attributes=attr, styles=styles)

            # Event
            edata = form.event.form
            event.name = edata.event_name.data
            event.description = edata.description.data
            event.date_start = edata.date_start.data
            event.date_end = edata.date_end.data
            event.date_publication = edata.date_publication.data
            event.date_ticket_sale = edata.date_ticket_release.data
            event.ticket_location = edata.location_tr.data
            event.host_id = host_id
            
            if edata.image.data:
                _, extension = os.path.splitext(edata.image.data.filename)
                filename = secure_filename(event.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension) 
                edata.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                event.image = 'images/uploads/' + filename

            #event.cohosts.clear()
            for cohost_id in edata.cohosts.data:
                if cohost_id != host_id:
                    cohost = Hosts.query.filter_by(id=cohost_id).first()
                    if cohost:
                        event.cohosts.append(cohost)
            

            # Biljetter
            count = 0
            for ticket in form.tickets:
                if (len(event.ticket_meta) > count):
                    #tdata = ticket.form
                    ticketToEdit_ID = event.ticket_meta[count].id
                    ticketToEdit = TicketMeta.query.get(ticketToEdit_ID)
                    ticketToEdit.name = ticket.form.name.data
                    ticketToEdit.price = ticket.form.price.data
                    ticketToEdit.description = ticket.form.description.data
                    oldCapacity = ticketToEdit.capacity
                    ticketToEdit.capacity = ticket.form.capacity.data
                    ticketToEdit.date_start = ticket.form.date_start.data
                    ticketToEdit.date_end = ticket.form.date_end.data
                    ticketToEdit.date_ticket_release = ticket.form.date_ticket_release_to_digital.data
                    ticketToEdit.location = ticket.form.location.data
                    ticketToEdit.digital_release = int(ticket.form.digital_release.data) 
            
                    if ticket.form.max_per_user.data is None:
                        ticketToEdit.max_per_user = -1
                    else:
                        ticketToEdit.max_per_user = ticket.form.max_per_user.data

                    if ticket.form.image.data:
                        _, extension = os.path.splitext(ticket.form.image.data.filename)
                        filename = secure_filename(event.name + ticketToEdit.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                        ticket.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                        ticketToEdit.image = 'images/uploads/' + filename

                    if (oldCapacity < ticketToEdit.capacity):
                        event.ticket_meta[count].generate_tickets(oldCapacity)
                    elif (oldCapacity > ticketToEdit.capacity):
                        event.ticket_meta[count].delete_tickets(oldCapacity - ticketToEdit.capacity)
                    count += 1
                else:
                    newticket = TicketMeta(
                        name=ticket.form.name.data,
                        price=ticket.form.price.data,
                        description=ticket.form.description.data,
                        capacity=ticket.form.capacity.data,
                        date_start=ticket.form.date_start.data,
                        date_end=ticket.form.date_end.data,
                        date_ticket_release=ticket.form.date_ticket_release_to_digital.data,
                        location=ticket.form.location.data,
                        digital_release=int(ticket.form.digital_release.data)
                    )

                    if ticket.form.max_per_user.data is None:
                        newticket.max_per_user = newticket.capacity
                    else:
                        newticket.max_per_user = ticket.form.max_per_user.data

                    if ticket.form.image.data:
                        _, extension = os.path.splitext(ticket.form.image.data.filename)
                        filename = secure_filename(event.name + newticket.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                        ticket.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                        newticket.image = 'images/uploads/' + filename

                    event.ticket_meta.append(newticket)
                    event.ticket_meta[-1].generate_tickets()
            
            #for ticket in event.ticket_meta:
                #ticket.generate_tickets()

            # Produkter
            if form.products and request.form.get('products') == "yes":
                count = 0
                for product in form.products:
                    if (len(event.products) > count):
                        productToEdit_ID = event.products[count].id
                        productToEdit = Products.query.get(productToEdit_ID)
                        productToEdit.name = product.form.name.data
                        productToEdit.price = product.form.price.data
                        productToEdit.capacity = product.form.capacity.data
                        productToEdit.description = product.form.description.data

                        if product.form.image.data:
                            _, extension = os.path.splitext(product.form.image.data.filename)
                            filename = secure_filename(event.name + productToEdit.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                            product.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                            productToEdit.image = 'images/uploads/' + filename
                            
                        #event.products.append(newproduct)
                    else: 
                        newproduct = Products(
                            name=product.form.name.data,
                            price=product.form.price.data,
                            capacity=product.form.capacity.data,
                            description=product.form.description.data
                        )

                        if product.form.image.data:
                            _, extension = os.path.splitext(product.form.image.data.filename)
                            filename = secure_filename(event.name + newproduct.name + datetime.now().strftime("%Y%m%d_%H%M%S%f") + extension)
                            product.form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                            newproduct.image = 'images/uploads/' + filename
                            
                        event.products.append(newproduct)
                    count += 1        

            db.session.commit()

            flash('Eventet uppdaterat!', 'success')
            return redirect('/events/')
    else:
       return render_template('errors/404.html'), 404

@host_blueprint.route("/api/getEventPreview/<int:host_id>/", methods=['POST'])
def getEventPreview(host_id):
    form = CreateEventForm(request.form)
    
    if request.form.get('products') == "no":
        form.products.entries.clear()

    form.event.form.description.data = bleach.clean(form.event.form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)
    for ticket in form.tickets:
        ticket.form.description.data = bleach.clean(ticket.form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)

    # Event
    edata = form.event.form
    event = Events(
        name=edata.event_name.data,
        description=edata.description.data,
        date_start=edata.date_start.data,
        date_end=edata.date_end.data,
        date_publication=edata.date_publication.data,
        date_ticket_sale=edata.date_ticket_release.data,
        ticket_location=edata.location_tr.data,
        host_id=host_id)

    event.host = Hosts.query.get(host_id)

    for cohost_id in edata.cohosts.data:
        if cohost_id != host_id:
            cohost = Hosts.query.filter_by(id=cohost_id).first()
            if cohost:
                event.cohosts.append(cohost)

    # Biljetter
    for ticket in form.tickets:
        newticket = TicketMeta(
            name=ticket.form.name.data,
            price=ticket.form.price.data,
            description=ticket.form.description.data,
            capacity=ticket.form.capacity.data,
            date_start=ticket.form.date_start.data,
            date_end=ticket.form.date_end.data,
            date_ticket_release=ticket.form.date_ticket_release_to_digital.data,
            location=ticket.form.location.data,
            digital_release=int(ticket.form.digital_release.data)
        )
        
        if ticket.form.max_per_user.data is None:
            newticket.max_per_user = -1
        else:
            newticket.max_per_user = ticket.form.max_per_user.data

        event.ticket_meta.append(newticket)
        
    return render_template('main/event.html', event=event, extends=True)


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


@host_blueprint.route("/hostAdmin/<int:id>")
def host(id):
    host = Hosts.query.filter_by(id=id).first()
    if host is not None and current_user.is_authenticated and current_user.is_host(host.id):
        return render_template('hostAdmin/events.html', title='Våra event', host = host, date=datetime.now().strftime("%Y%m%d_%H%M%S%f"), host_sidenav=True)
    return redirect('users.login')


@host_blueprint.route("/hostAdmin/account/<int:id>", methods=['GET', 'POST'])
def account(id):
    host = Hosts.query.filter_by(id=id).first()
    if host is not None and current_user.is_authenticated and current_user.is_host(host.id):
        form = UpdateAccountForm()
        
        if form.validate_on_submit():
            form.description.data = bleach.clean(form.description.data, tags=tags, attributes=attr, styles=styles, strip=True)
            host.description = form.description.data
            host.long_name = form.name.data
            host.short_name = form.short_name.data

            if form.image.data:
                _, extension = os.path.splitext(form.image.data.filename)
                filename = secure_filename("hostimage" + host.short_name + extension)
                form.image.data.save(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename))
                host.image = 'images/uploads/' + filename
            
            db.session.commit()
            flash('Kontot är uppdaterat!', 'success')
            return redirect("/hostAdmin/account/" + str(id))

        elif request.method == 'GET':
            form.description.data = host.description
            form.image.data = host.image
            form.name.data = host.long_name
            form.short_name.data = host.short_name
        return render_template('/hostAdmin/account.html', title='Konto', form=form, host=host, date=datetime.now().strftime("%Y%m%d_%H%M%S%f"), host_sidenav=True)
    
    return redirect(url_for('users.login', next=request.url))


@host_blueprint.route("/hostAdmin/account/defaultprofile/<int:id>", methods=['DELETE'])
def accountProfile(id):
    host = Hosts.query.filter_by(id=id).first()
    
    if host is not None and current_user.is_authenticated and current_user.is_host(host.id):
        filename, ext = os.path.splitext(host.image)
        host.image = 'images/defaultProfile.jpg'
        
        if os.path.exists(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], 'hostimage' + host.short_name + ext)):
            os.remove(os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], 'hostimage' + host.short_name + ext))
            
        db.session.commit()
        return "Success"
    return "Not allowed"


@host_blueprint.route("/hostAdmin/event/<int:event_id>", methods=['GET','POST'])
def hostEvent(event_id):
    event = Events.query.get(event_id)
    host = Hosts.query.filter_by(id=event.host_id).first()
    #form = PresaleTicketForm()
    
    if host is not None and current_user.is_authenticated and isEventHost(event_id):
        return render_template('hostAdmin/handle_event.html', title=event.name, host=host, event=event, date=datetime.now().strftime("%Y%m%d_%H%M%S%f"), host_sidenav=True)
    return redirect('users.login')


def reserveFormToDict(form):
    error = dict()
    items = dict()
    for data in form:
        if 'amount-' in data:
            
            id = int(data[7:])
            if form.get('amount-'+str(id)):
                ticket_meta_id = id
                ticket_meta = TicketMeta.query.get(ticket_meta_id)
                amount = form.get('amount-'+str(ticket_meta_id))
                items['amount'] = amount
                items['ticket'] = ticket_meta 
                
                if int(ticket_meta.avaliable_tickets()) == 0:
                    error[data] = 'Finns inga tillgängliga biljetter kvar'
                elif int(ticket_meta.avaliable_tickets()) < int(amount):
                    error[data] = 'Endast ' + str(ticket_meta.avaliable_tickets()) + ' tillgängliga biljetter kvar'
                elif int(amount) <= 0:
                    error[data] = 'Antalet biljetter måste vara större än 0'
                
                if form.get('email-'+str(ticket_meta_id)):
                    user = Users.query.filter_by(id=request.form['email-'+str(ticket_meta_id)]).first()
                    if user is None:
                        error['email-'+str(ticket_meta_id)] = 'Den användaren finns inte'
                    else:
                        items['user'] = user

                else:
                    error['email-'+str(ticket_meta_id)] = 'Välj en mottagare'
            if (not form.get('amount-'+str(id))) and form.get('email-'+str(id)):
                error[data] = 'Välj antal biljetter'
            #if (not form.get('amount-'+str(id))) and (not form.get('email-'+str(id))):
            #    error[data] = 'Välj antal biljetter'

    return items, error


@host_blueprint.route("/api/hostAdmin/validateReserveForm/<int:event_id>", methods=['POST'])
def validateReserveForm(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/event/' + event_id))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))
        
    _, error = reserveFormToDict(request.form)

    if len(error) > 0:
        return jsonify(error)
    return jsonify(True)


@host_blueprint.route('/api/hostAdmin/reservetickets/<int:event_id>', methods=['POST'])
def reserveticket(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/ticket_sale/' + event_id))
    if not isEventHost(event_id):
        return redirect(url_for('main.home'))

    items, error = reserveFormToDict(request.form)
    user = items.get('user')
    ticket_meta = items.get('ticket')
  
    for i in range(int(items.get('amount'))):
        ticket = ticket_meta.get_first_free_ticket()
        if ticket is not None:
            ticket.reserve_ticket(user.id)
        else:
            error[id] = 'Biljett ' + user.name + ' kunde ej reserveras.'
    if len(error) > 0:
        return jsonify(error)
    else:
        flash('Biljetterna till '+ ticket_meta.name + ' reserverades till ' + user.name, 'info')
        return jsonify(True)

"""
Route länken som raderar ett event
"""
@host_blueprint.route('/api/hostAdmin/remove_event/<int:event_id>')
def removeEvent(event_id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next='/hostAdmin/ticket_sale/' + event_id))
    if not current_user.is_admin or not isEventHost(event_id):
        return redirect(url_for('main.home'))

    event = Events.query.get(event_id)
    host_id = event.host_id
    for item in event.products:
        db.session.delete(item)

    try:
        for ticket_meta in event.ticket_meta:
            for ticket in ticket_meta.tickets:
                for transaction in ticket.transactions:
                        db.session.delete(transaction)
                db.session.delete(ticket)
            db.session.delete(ticket_meta)
        db.session.delete(event)
        db.session.commit()
    except:
        flash('Kunde inte ta bort eventet', 'danger')
        return redirect('/hostAdmin/event/' + str(event_id))

    return redirect('/hostAdmin/' + str(host_id))