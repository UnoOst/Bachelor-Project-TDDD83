import os

from flask_login import current_user
from flask_uploads import (IMAGES, UploadSet, configure_uploads,
                           patch_request_class)
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (BooleanField, FieldList, Form, FormField, IntegerField,
                     PasswordField, RadioField, SelectMultipleField,
                     StringField, SubmitField, TextAreaField, HiddenField)
from wtforms.fields.html5 import DateTimeLocalField
from wtforms.validators import (Email, EqualTo, InputRequired, Length,
                                Optional, ValidationError, DataRequired)

from ..models import Events, Hosts, Users, Tickets, TicketMeta
from wtforms.widgets import HiddenInput
import datetime

photos = UploadSet('photos', IMAGES)

class ProductForm(Form):
    name = StringField('Produkt', validators=[InputRequired()])
    price = IntegerField('Pris', validators=[DataRequired()])
    capacity = IntegerField('Antal', description='Antal produkter tillgängliga för försäljning - Viktigt med rätt antal', validators=[DataRequired()])
    description = StringField('Beskrivning', validators=[Optional()])
    image = FileField('Bild', validators=[FileAllowed(photos, 'Endast bilder tillåts!')])
    
    def validate_price(self, price):
        if self.price.data >= 0:
            return True
        if self.price.data < 0:
            self.price.errors.append('Priset för en biljett får ej vara negativt')
            return False
        return True

    def insertOldValues(self, products):
        self.name.data = products.name
        self.price.data = products.price
        self.capacity.data = products.capacity
        self.description.data = products.description

    def validate_capacity(self, capacity):
        if self.capacity.data > 0:
            return True
        if self.capacity.data < 1:
            self.capacity.errors.append('Antalet produkter måste vara större än 0')
            return False
        return True  


class TicketForm(Form):
    digital_release = RadioField('Digitalt släpp', choices=[('0', 'Fysiskt släpp'),('1', 'Digitalt släpp')], validators=[InputRequired()], default='0')
    name = StringField('Biljettnamn', description='Namn på evenemanget som biljett går till', validators=[InputRequired('Namn för event krävs')])
    location = StringField('Lokal', validators=[InputRequired('Lokal för biljetten krävs')])
    capacity = IntegerField('Kapacitet', validators=[DataRequired('Kapacitet för biljetten krävs')])
    max_per_user = IntegerField('Köpgräns', description='Max antal biljetter en person kan köpa', validators=[Optional()])
    price = IntegerField('Pris', validators=[DataRequired('Pris för biljetten krävs')])
    description = TextAreaField('Beskrivning', validators=[Optional()])
    date_start = DateTimeLocalField('Startdatum', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    date_end = DateTimeLocalField('Slutdatum', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    date_ticket_release_to_digital = DateTimeLocalField('Datum för digital biljettförsäljning', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    image = FileField('Bild', validators=[FileAllowed(photos, 'Endast bilder tillåts!')])
    helpID = HiddenField('helpID')
    
    def validate_capacity(self, capacity):
        if self.helpID.data != '':
            if self.capacity.data < TicketMeta.query.get(int(self.helpID.data)).capacity:               
                soldAndReserved = TicketMeta.query.get(int(self.helpID.data)).sold_tickets()              
                if self.capacity.data < soldAndReserved:             
                    self.capacity.errors.append('Minskningen i antal biljetter får ej understiga antalet redan sålda biljetter: ' + str(soldAndReserved))
                    return False
            else:
                return True
        else: 
            return True
        if self.capacity.data > 0:
            return True
        if self.capacity.data < self.max_per_user.data:
             self.capacity.errors.append('Antal biljetter får ej vara mindre än max antalet för köp')
             return False
        if self.capacity.data < 1:
            self.capacity.errors.append('Antalet biljetter måste vara större än 0')
            return False
        
        return True    

    def validate_price(self, price):
        if self.price.data >= 0:
            return True
        if self.price.data < 0:
            self.price.errors.append('Priset för en biljett får ej vara negativt')
            return False
        return True

    def validate_date_start(self, date_start):
        if self.date_start.data < datetime.datetime.now():
            self.date_start.errors.append('Startatumet måste vara senare än dagens datum')
            return False
        if self.date_start.data <= self.date_end.data:
            return True
        if self.date_start.data > self.date_end.data:
            self.date_start.errors.append('Startdatumet måste vara innan slutdatumet')
            return False
        return True

    def validate_date_end(self, date_end):
        if self.date_end.data < datetime.datetime.now():
            self.date_end.errors.append('Slutdatumet måste vara senare än dagens datum')
            return False
        if self.date_end.data >= self.date_start.data:
            return True
        if self.date_end.data < self.date_start.data:
            self.date_start.errors.append('Slutdatumet måste vara efter startdatumet')
            return False
        return True
    
    def validate_date_ticket_release_to_digital(self, date_ticket_release_to_digital):
        if self.date_ticket_release_to_digital.data < datetime.datetime.now():
            self.date_ticket_release_to_digital.errors.append('Datumet för att övergå till digial försäljning måste vara senare än dagens datum')
            return False
        if self.date_ticket_release_to_digital.data < self.date_end.data:
            return True
        if self.date_ticket_release_to_digital.data > self.date_end.data:
            self.date_ticket_release_to_digital.errors.append('Datumet för att övergå till digital försäljning måste vara tidigare än slutdatumet')
            return False
        return True

    def validate_max_per_user(self, max_per_user):
        if self.max_per_user.data is None:
            return True
        if self.max_per_user.data > self.capacity.data:
            self.max_per_user.errors.append('Antal biljetter per köpare får ej vara större än antalet biljetter')
            return False
        if self.max_per_user.data < 1:
            self.max_per_user.errors.append('Antal biljetter per köpare måste vara minst 1')
            return False
        return True
     
    def insertOldValues(self, ticket):
        if (ticket.digital_release):
            self.digital_release.data = '1'
        else:
            self.digital_release.data = '0'
        self.name.data = ticket.name
        self.location.data = ticket.location
        self.capacity.data = ticket.capacity
        if (ticket.max_per_user == ticket.capacity):
            self.max_per_user.data = ""
        else:
            self.max_per_user.data = ticket.max_per_user
        self.price.data = ticket.price
        self.description.data = ticket.description
        self.date_start.data = ticket.date_start
        self.date_end.data = ticket.date_end
        self.date_ticket_release_to_digital.data = ticket.date_ticket_release
        self.helpID.data = ticket.id


class EventForm(Form):
    event_name = StringField('Evenemang', validators=[InputRequired(), Length(min=1, max=99)])
    description = TextAreaField('Beskrivning', validators=[Optional()])
    date_start = DateTimeLocalField('Startdatum', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    date_end = DateTimeLocalField('Slutdatum', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    date_publication = DateTimeLocalField('Publiceringsdatum', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    date_ticket_release = DateTimeLocalField('Biljettsläpp', format='%Y-%m-%dT%H:%M', validators=[InputRequired()])
    location_tr = StringField('Plats för biljettsläpp', validators=[InputRequired()])
    cohosts = SelectMultipleField('Medarrangörer', choices=[], coerce=int)
    image = FileField('Bild', validators=[FileAllowed(photos, 'Endast bilder tillåts!')])
    edit = HiddenField('editOrCreate', default=False)

    def validate_date_ticket_release(self, date_ticket_release):
        if self.edit.data == False:
            if self.date_ticket_release.data < datetime.datetime.now():
                self.date_ticket_release.errors.append('Biljettsläppet får ej vara tidigare än dagens datum')
                return False
        if self.date_ticket_release.data < self.date_publication.data:
            self.date_ticket_release.errors.append('Biljettsläppsdatumet måste vara efter publikationsdatumet')
            return False
        if self.date_ticket_release.data > self.date_start.data:
            self.date_ticket_release.errors.append('Biljettsläppsdatumet måste vara före startdatumet')
            return False
        if self.date_ticket_release.data > self.date_end.data:
            self.date_ticket_release.errors.append('Biljettsläppsdatumet måste vara före slutdatumet')
            return False
        return True

    def validate_date_end(self, date_end):
        if self.date_end.data < datetime.datetime.now():
            self.date_end.errors.append('Slutdatumet får ej vara tidigare än dagens datum')
            return False
        if self.date_start.data > self.date_end.data:
            self.date_end.errors.append('Slutdatumet måste vara efter startdatumet')
            return False    
        if self.date_end.data < self.date_publication.data:
            self.date_end.errors.append('Slutdatumet måste vara efter publikationsdatumet')
            return False
        if self.date_end.data < self.date_ticket_release.data:
            self.date_end.errors.append('Slutdatumet måste vara efter biljettsläppsdatumet')
            return False
        return True

    def validate_date_start(self, start_end):
        if self.date_start.data < datetime.datetime.now():
            self.date_start.errors.append('Startdatumet får ej vara tidigare än dagens datum')
            return False
        if self.date_start.data > self.date_end.data:
            self.date_start.errors.append('Startdatumet måste vara innan slutdatumet')
            return False
        if self.date_start.data < self.date_publication.data:
            self.date_start.errors.append('Startdatumet måste vara efter publikationsdatumet')
            return False
        return True
    
    def insertOldValues(self, event):
        self.event_name.data = event.name
        self.description.data = event.description
        self.date_start.data = event.date_start
        self.date_end.data = event.date_end
        self.date_publication.data = event.date_publication
        self.date_ticket_release.data = event.date_ticket_sale
        self.location_tr.data = event.ticket_location  
        self.edit.data = True 

    def validate_date_publication(self, date_publication):
        if self.date_publication.data > self.date_ticket_release.data:
            self.date_publication.errors.append('Publikationsdatumet måste vara innan biljettsläppsdatumet')
            return False
        if self.date_publication.data > self.date_start.data:
            self.date_publication.errors.append('Publikationsdatumet måste vara innan startdatumet')
            return False
        if self.date_publication.data > self.date_end.data:
            self.date_publication.errors.append('Publikationsdatumet måste vara innan slutdatumet')
            return False
        return True


class CreateEventForm(FlaskForm):
    event = FormField(EventForm)

    products = FieldList(FormField(ProductForm),
        min_entries=0,
        max_entries=20)
    tickets = FieldList(FormField(TicketForm),
        min_entries=1,
        max_entries=20)


class UpdateAccountForm(FlaskForm):
    name = StringField('Namn', validators=[InputRequired()])
    short_name = StringField('Förkortning', validators=[InputRequired()])
    description = TextAreaField('Beskrivning')
    image = FileField('Profilbild', validators=[FileAllowed(photos, 'Endast bilder tillåts!')])
    submit = SubmitField('Uppdatera')