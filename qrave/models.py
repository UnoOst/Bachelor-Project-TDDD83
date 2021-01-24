from datetime import datetime, date
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from qrave import db, login_manager, bcrypt, config
from flask_login import UserMixin
from sqlalchemy.orm import load_only
import string 
import random
from enum import Enum

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(Users).get(int(user_id))

UsersInRoles = db.Table('users_in_roles', db.Model.metadata,
    db.Column('user', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role', db.Integer, db.ForeignKey('roles.id'), primary_key=True))


UsersInHosts = db.Table('users_in_hosts', db.Model.metadata,
    db.Column('user', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('host', db.Integer, db.ForeignKey('hosts.id'), primary_key=True))


EventCoHosts = db.Table('event_co_hosts', db.Model.metadata, 
    db.Column('host', db.Integer, db.ForeignKey('hosts.id'), primary_key=True),
    db.Column('event', db.Integer, db.ForeignKey('events.id'), primary_key=True))


EventVisibleFor = db.Table('event_visible_for', db.Model.metadata, 
    db.Column('roles', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('event', db.Integer, db.ForeignKey('events.id'), primary_key=True))


TicketsInPayments = db.Table('tickets_in_payments', db.Model.metadata,
    db.Column('payment', db.Integer, db.ForeignKey('payments.id'), primary_key=True),
    db.Column('ticket', db.Integer, db.ForeignKey('tickets.id'), primary_key=True))


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    liuid = db.Column(db.String(8), unique=True, nullable=True)
    name = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(16), nullable=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    
    roles = db.relationship("Roles", secondary=UsersInRoles)
    hosts = db.relationship("Hosts", secondary=UsersInHosts)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    def get_verify_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}).decode('utf-8')


    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf8")
    
    def set_is_verified(self, status):
        self.is_verified = status

    def is_admin(self):
        for role in self.roles:
            if role.name == "admin":
                return True
        return False

    def is_host(self, host_id: int=None):
        if host_id is None and len(self.hosts) > 0:
            return True
        else:
            for host in self.hosts:
                if host.id == host_id:
                    return True
        return False
    
    def get_user_by_id(id):
        return Users.query.filter_by(id=id)

    @staticmethod
    def verify_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return Users.query.get(user_id)

    def __repr__(self):
        return f"User('{self.liuid}', '{self.name}', '{self.email}', '{self.phone}')\n\tRoles: {self.roles}\n\tHosts: {self.hosts}\n\tTickets: {self.tickets}"


class Transactions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)

    def __repr__(self):
        return self.description

    class Type(Enum):
        CREATE = "Created"
        BOUGHT = "Bought"
        OWNER_CHANGE = "Owner change"
        RESERVED = "Reserved"


class Tickets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qrcode = db.Column(db.String(30), nullable=False, unique=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_used = db.Column(db.DateTime, nullable=True)
    used = db.Column(db.Boolean, nullable=False, default=False)
    date_for_sale = db.Column(db.DateTime, nullable=True)
    reserved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    meta_id = db.Column(db.Integer, db.ForeignKey('ticket_meta.id'), nullable=False)

    reserved_by = db.relationship('Users', backref='reserved_tickets', foreign_keys=[reserved_by_id])
    owner = db.relationship('Users', backref='tickets', foreign_keys=[owner_id])
    transactions = db.relationship("Transactions", backref="ticket")
    meta = db.relationship("TicketMeta", backref="tickets")

    def __repr__(self):
        return self.qrcode

    def create_transaction(self, transaction_type: Transactions.Type, owner: int=None, new_owner: int=None, commit: bool=True):
        if transaction_type == Transactions.Type.CREATE:
            self.transactions.append(Transactions(description=transaction_type.value))
        elif transaction_type == Transactions.Type.OWNER_CHANGE:
            self.transactions.append(Transactions(description=f"{transaction_type.value} from user_id: {owner} to user_id: {new_owner}"))
        elif transaction_type == Transactions.Type.BOUGHT:
            self.transactions.append(Transactions(description=f"{transaction_type.value} by user_id: {owner}"))
        elif transaction_type == Transactions.Type.RESERVED:
            self.transactions.append(Transactions(description=f"{transaction_type.value} by user_id: {self.reserved_by_id}"))
        if commit:
            db.session.commit()

    def transfer_ticket(self, new_owner: int=None):
        if (new_owner is not None and self.owner is not None):
            self.create_transaction(Transactions.Type.OWNER_CHANGE, self.owner, new_owner)
        else:
            self.create_transaction(Transactions.Type.BOUGHT, new_owner)
        self.owner_id = new_owner
        self.reserved_by = None
        self.date_for_sale = None
        tickets = Tickets.query.options(load_only('qrcode')).all()
        qrcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=current_app.config['QR_CODE_LENGTH']))
        while qrcode in tickets:
            qrcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=current_app.config['QR_CODE_LENGTH']))
        self.qrcode = qrcode
        db.session.commit()
    
    def reserve_ticket(self, new_reserve_id: int=None, commit: bool=True):
        self.create_transaction(Transactions.Type.RESERVED, new_reserve_id, commit)
        self.reserved_by_id = new_reserve_id
        if commit:
            db.session.commit()

    def check_expired(self):
        today = datetime.now()
        if self.meta.date_end < today:
            self.used = True
            self.date_used = today
            db.session.commit()


class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.Text, nullable=False, default='images/defaultEvent.jpg')
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_start = db.Column(db.DateTime, nullable=False)
    date_end = db.Column(db.DateTime, nullable=False)
    date_publication = db.Column(db.DateTime, nullable=False)
    date_ticket_sale = db.Column(db.DateTime, nullable=False)
    ticket_location = db.Column(db.String(100), nullable=True)
    host_id = db.Column(db.Integer, db.ForeignKey('hosts.id'), nullable=False)

    ticket_meta = db.relationship("TicketMeta", backref=db.backref("event", uselist=False))
    products = db.relationship("Products", backref="event")
    cohosts = db.relationship("Hosts", secondary=EventCoHosts)
    visible_for = db.relationship("Roles", secondary=EventVisibleFor)

    def __repr__(self):
        return self.name


class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.Text, nullable=False, default='images/defaultProduct.jpg')
    capacity = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)

    def __repr__(self):
        return self.name


class TicketMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.Text, nullable=False, default='images/defaultTicket.jpg')
    description = db.Column(db.Text, nullable=True)
    capacity = db.Column(db.Integer, nullable=False)
    max_per_user = db.Column(db.Integer, nullable=False)
    date_start = db.Column(db.DateTime, nullable=False)
    date_end = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.Text, nullable=False)
    digital_release = db.Column(db.Boolean, nullable=False, default=False)
    date_ticket_release = db.Column(db.DateTime, nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)

    def __repr__(self):
        return f"Namn: {self.name}\nPris: {self.price}\nDatum: {self.date_start}"

    def delete_tickets(self, nrToDelete):
        listOfFreeTickets = Tickets.query.filter_by(meta_id=self.id).filter(Tickets.owner_id==None, Tickets.reserved_by_id==None).all()
        for i in range(nrToDelete):
            ticket = listOfFreeTickets[i]
            Transactions.query.filter_by(ticket_id=ticket.id).delete()
            db.session.delete(ticket)
        db.session.commit()    
            

    def generate_tickets(self, ticketsAlreadyMade: int=0):
        tickets = Tickets.query.options(load_only('qrcode')).all()
        for i in range(self.capacity - ticketsAlreadyMade):
            qrcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=current_app.config['QR_CODE_LENGTH']))
            while qrcode in tickets:
                qrcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=current_app.config['QR_CODE_LENGTH']))
            ticket = Tickets(meta_id=self.id, qrcode=qrcode)
            ticket.create_transaction(Transactions.Type.CREATE, commit=False)
            db.session.add(ticket)
        db.session.commit()

    def get_first_free_ticket(self):
        return Tickets.query.filter_by(meta_id=self.id, owner_id=None, reserved_by_id=None, used=False).first()

    def unsold_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.owner_id==None).count()
    
    def sold_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.owner_id!=None).count()

    def reserved_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.reserved_by_id!=None).count()
    
    def avaliable_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.owner_id==None).count() - Tickets.query.filter_by(meta_id=self.id).filter(Tickets.reserved_by_id!=None).count()

    def get_second_hand_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.date_for_sale!=None, Tickets.used==False, Tickets.reserved_by_id==None).order_by(Tickets.date_for_sale.desc())
    
    def get_first_hand_tickets(self):
        return Tickets.query.filter_by(meta_id=self.id).filter(Tickets.owner_id==None, Tickets.reserved_by_id==None, Tickets.used==False)


class Roles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

    def __repr__(self):
        return self.name


class Hosts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(10), unique=True)
    long_name = db.Column(db.String(100), unique=True)
    image = db.Column(db.Text, nullable=False, default='images/defaultHost.jpg')
    description = db.Column(db.Text, nullable=True)
    incognito = db.Column(db.Boolean, nullable=False, default=False)
    
    events = db.relationship("Events", backref="host")

    def __repr__(self):
        return self.short_name


class Payments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    swish_url = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tickets = db.relationship("Tickets", secondary=TicketsInPayments)


class Logs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    logs = db.relationship('LogText', backref='log')


class LogText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('logs.id'), nullable=False)
    text = db.Column(db.Text())
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return self.text