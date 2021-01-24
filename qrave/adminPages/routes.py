from flask import render_template, request, Blueprint, Response, url_for, redirect
from flask_login import current_user
import json
import time
import random
from qrave import db
from datetime import datetime
from ..models import Users, Events, TicketMeta, Tickets

admin = Blueprint('stats', __name__)


@admin.route("/admin/scan/", methods=['GET', 'POST'])
def scan():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next="/admin/scan"))
    if not current_user.is_admin():
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        qrcode = request.form['qrcode']
        ticket = Tickets.query.filter_by(qrcode=qrcode).first()
        if ticket:
            if ticket.meta.date_start < datetime.now() and datetime.now() < ticket.meta.date_end:
                return json.dumps({'message': 'Biljetten är utanför datumtiderna för eventet!', 'status': 'primary'})
            if ticket.used:
                return json.dumps({'message': f'Redan använd! Biljetten användes: {ticket.date_used.date()} {ticket.date_used.time()}', 'status': 'warning'})
            else:
                ticket.used = True
                ticket.date_used = datetime.now()
                db.session.commit()
                return json.dumps({'message': 'Giltig biljett!', 'status': 'success'})
        else:
            return json.dumps({'message': 'Biljetten kunde inte hittas i systemet!', 'status': 'danger'})
    return render_template('admin/scan.html', title='Scanna', admin_sidenav=True)


@admin.route("/admin/stats/")
def statshome():
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next="/admin/scan"))
    if not current_user.is_admin():
        return redirect(url_for('main.home'))

    events = Events.query.order_by(Events.date_start.asc())
    return render_template('admin/statshome.html', events=events, title='Statstik', admin_sidenav=True)


@admin.route("/admin/stats/<int:id>")
def stats(id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next="/admin/scan"))
    
    from ..hostAdmin.routes import isEventHost
    meta = TicketMeta.query.get(id)
    if not current_user.is_admin() and not isEventHost(meta.event.id):
        return redirect(url_for('main.home'))
    if isEventHost(meta.event.id):
        host = meta.event.host
        return render_template('admin/stats.html', title='Statstik', meta=meta, host=host, host_sidenav=True)
    return render_template('admin/stats.html', title='Statstik', meta=meta, admin_sidenav=True)


@admin.route("/api/stats/<int:id>")
def getCurrentStats(id):
    if not current_user.is_authenticated:
        return redirect(url_for('users.login', next="/admin/scan"))
    from ..hostAdmin.routes import isEventHost
    meta = TicketMeta.query.get(id)
    if not current_user.is_admin() and not isEventHost(meta.event.id):
        return redirect(url_for('main.home'))

    dates = Tickets.query.filter_by(used=True, meta_id=id).order_by(Tickets.date_used)
    y=0
    r = []
    if dates is not None:
        for date in dates:
            y += 1
            r.append(dict(t=date.date_used.strftime("%Y-%m-%dT%H:%M"), y=y))
        ret = json.dumps(r)
    return ret
