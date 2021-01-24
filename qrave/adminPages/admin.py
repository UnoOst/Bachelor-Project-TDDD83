import os.path as op
from http import HTTPStatus
from flask import abort, redirect, request, url_for
from flask_admin import AdminIndexView
from flask_admin.base import Admin, expose
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from flask_login import current_user
from qrave import db
from ..models import *

path = op.join(op.dirname("qrave/static/"), 'images')


def create_admin():
    admin = Admin(index_view=MyView())
    admin.add_view(UsersView(Users, db.session, endpoint="user"))
    admin.add_view(TicketsView(Tickets, db.session))
    admin.add_view(TransactionsView(Transactions, db.session))
    admin.add_view(EventsView(Events, db.session))
    admin.add_view(TicketMetaView(TicketMeta, db.session))
    admin.add_view(BaseView(Products, db.session))
    admin.add_view(BaseView(Roles, db.session))
    admin.add_view(HostsView(Hosts, db.session))
    admin.add_view(BaseView(Payments, db.session))
    admin.add_view(LogView(Logs, db.session))
    admin.add_view(ImageView(path, '/static/images/', name='Bilder'))

    return admin


class AdminSecurityMixin(object):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('users.login', next=request.url))


class MyView(AdminSecurityMixin, AdminIndexView):
    def is_visible(self):
        return False


class ImageView(AdminSecurityMixin, FileAdmin):
    form_base_class = SecureForm


class BaseView(AdminSecurityMixin, ModelView):
    can_view_details = True
    form_base_class = SecureForm


class LogView(AdminSecurityMixin, ModelView):
    column_list = ['user_id', 'event_id']
    column_details_list = ('logs', 'user_id', 'event_id')
    can_view_details = True
    form_base_class = SecureForm


class UsersView(AdminSecurityMixin, ModelView):
    form_excluded_columns = ('password')
    column_list = ['name', 'email', 'liuid', 'phone', 'hosts', 'roles']
    column_searchable_list = ['liuid', 'name', 'email', 'hosts.short_name']
    column_labels = {'liuid':'Liuid', 'name':'Name', 'hosts.short_name':'Host', 'email':'Email'}
    column_filters = ['hosts.short_name', 'roles.name']
    column_choices = {
        'roles.name': [
            ('admin', 'Admin'),
        ]
    }
    column_details_list = ('name', 'email', 'liuid', 'phone', 'hosts', 'roles')
    can_create = False
    can_delete = False
    can_view_details = True
    form_base_class = SecureForm

        
class TicketsView(AdminSecurityMixin, ModelView):
    column_list = ['qrcode', 'date_created', 'used', 'date_used', 'transactions', 'meta.name', 'meta.event.name', 'owner.liuid']
    column_filters = ('transactions.description', 'qrcode', 'meta.name')
    column_labels = {'owner.liuid':'Owner', 'meta.name':'Ticket name', 'meta.event.name':'Event'}
    column_details_list = ('qrcode', 'date_created', 'used', 'date_used', 'transactions', 'meta.name', 'meta.event.name', 'owner.liuid')
    can_export = True
    can_delete = False
    can_view_details = True
    can_create = False
    can_edit = False
    form_base_class = SecureForm


class EventsView(AdminSecurityMixin, ModelView):
    column_exclude_list = ['description']
    can_export = True
    can_delete = True
    can_view_details = True
    can_create = False
    can_edit = True
    form_base_class = SecureForm


class TicketMetaView(AdminSecurityMixin, ModelView):
    column_exclude_list = ['description']
    form_excluded_columns = ('tickets')
    can_export = True
    can_delete = False
    can_view_details = True
    can_create = False
    can_edit = True
    form_base_class = SecureForm


class TransactionsView(AdminSecurityMixin, ModelView):
    column_list = ['date', 'description', 'ticket']
    column_searchable_list = {'ticket.qrcode'}
    column_labels = {'ticket.qrcode':'QRcode', 'ticket':'QRcode', 'ticket.transactions': 'All transactions for this ticket'}
    column_details_list = ('date', 'description', 'ticket', 'ticket.transactions')
    column_choices = {
        'description': [
            (Transactions.Type.CREATE.value, Transactions.Type.CREATE.value),
            (Transactions.Type.BOUGHT.value, Transactions.Type.BOUGHT.value),
            (Transactions.Type.OWNER_CHANGE.value, Transactions.Type.OWNER_CHANGE.value),
        ]
    }
    column_filters = ['description']
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
    can_create = False
    form_base_class = SecureForm


class HostsView(AdminSecurityMixin, ModelView):
    form_columns = ['short_name', 'long_name', 'image', 'description']
    column_list = ['short_name', 'long_name', 'image', 'description']
    can_view_details = True
    form_base_class = SecureForm
