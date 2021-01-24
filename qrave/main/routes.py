from flask import render_template, request, Blueprint, redirect, url_for, flash
from qrave import db
from ..models import Users, Events, Hosts
import datetime
from ..users.forms import (ContactForm)
from ..users.utils import send_contact_email

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home/")
def home():
    return redirect(url_for('main.events'))


@main.route("/events/")
def events():
    today = datetime.datetime.now()
    todayplus = datetime.datetime.now() + datetime.timedelta(days=10)
    events = Events.query.filter(Events.date_publication <= today, today <= Events.date_end).order_by(Events.date_start.asc()).all()
    return render_template('main/events.html', title='Events', events=events)


@main.route("/event/<int:id>")
def event(id):
    event = Events.query.filter_by(id=id).first()
    return render_template('main/event.html', title='Event', event=event)


@main.route("/hosts/<int:id>")
def host(id):
    host = Hosts.query.get(id)
    today = datetime.datetime.now()
    todayplus = datetime.datetime.now() + datetime.timedelta(days=10)
    events = Events.query.filter(Events.date_publication <= today, today <= Events.date_end, Events.host_id==host.id).order_by(Events.date_start.asc()).all()
    return render_template('main/host.html', title=host.short_name, host=host,events=events)


@main.route("/tickets/")
def tickets():
    tickets = Ticket.query.all()
    return render_template('main/tickets.html', title='Biljetter', tickets=tickets)


@main.route("/about/")
def about():
    return render_template('main/about.html', title='Om oss')


@main.route("/contact/", methods=['GET','POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        send_contact_email(form.name.data, form.email.data, form.topic.data)
        flash("Vi har tagit emot ditt medelande och hör av oss så fort vi kan", "success")
        return redirect("/contact")
    return render_template('main/contact.html', title='Kontakt', form=form)


@main.route("/terms/")
def terms():
    return render_template('main/terms.html', title='Villkor')

@main.route("/faq/")
def faq():
    return render_template('main/faq.html', title='FAQ')

@main.route("/hosts/")
def hosts():
    hosts = Hosts.query.order_by(Hosts.long_name)
    return render_template('main/hosts.html', title='Arrangörer', hosts=hosts)
