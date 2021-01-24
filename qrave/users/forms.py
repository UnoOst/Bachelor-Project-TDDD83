from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, FormField, FieldList, IntegerField, Form
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms.widgets import HiddenInput
from flask_login import current_user
from ..models import Users



class LoginForm(FlaskForm):
    email = StringField('Mail', validators=[DataRequired('Vad är din mailadress?'), Email('Det där är inte en mailadress.')])
    password = PasswordField('Lösenord', validators=[DataRequired('Vad är ditt lösenord?')])
    remember = BooleanField('Kom ihåg mig')
    submit = SubmitField('Logga in')


class RegistrationForm(FlaskForm):
    name = StringField('Namn', validators=[DataRequired('Vad heter du?'), Length(min=2, max=60)])
    liuid = StringField('LiU-ID', validators=[Length(max=8)])
    phone = StringField('Telefonnummer', validators=[Length(max=16)])
    email = StringField('Mail', validators=[DataRequired('Vad är din mailadress?'), Email('Det där är inte en mailadress.'), Length(min=5, max=120)])
    password = PasswordField('Lösenord', validators=[DataRequired('Du måste fylla i ett lösenord'), Length(max=60)])
    confirm_password = PasswordField('Bekräfta lösenord', validators=[DataRequired('Du måste fylla i ett lösenord'), EqualTo('password', 'Lösenorden matchar inte.')])
    accept_terms = BooleanField('Ja, jag godkänner', validators= [DataRequired()])
    submit = SubmitField('Registrera')

    def validate_liuid(self, liuid):
        user = Users.query.filter_by(liuid=liuid.data).first()
        if user and liuid.data.strip() != "":
            raise ValidationError('Det LiU-ID är upptaget. Har du redan ett konto?')

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Den mailadressen är upptagen. Välj en annan eller återställ ditt lösenord!')


class UpdateAccountForm(FlaskForm):
    name = StringField('Namn', validators=[DataRequired('Vad heter du?'), Length(min=2, max=20)])
    email = StringField('Mail', validators=[DataRequired('Vad är din mailadress?'), Email('Det där är inte en mailadress.')])
    phone = StringField('Telefonnummer', validators=[Length(max=16)])
    liuid = StringField('LiU-ID', validators=[Length(max=8)])
    submit = SubmitField('Uppdatera')

    def validate_liuid(self, liuid):
        if liuid.data != current_user.liuid:
            user = Users.query.filter_by(liuid=liuid.data).first()
            if user:
                raise ValidationError('Det LiU-ID är upptaget.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = Users.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Den mailadressen är upptagen. Välj en annan eller återställ ditt lösenord!')


class RequestResetForm(FlaskForm):
    email = StringField('Mail', validators=[DataRequired('Vad är din mailadress?'), Email('Det där är inte en mailadress.')])
    submit = SubmitField('Begär lösenordsåterställning')

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Det finns inget konto med den mailadressen. Du måste registrera dig först.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Lösenord', validators=[DataRequired('Du måste fylla i ett lösenord.')])
    confirm_password = PasswordField('Bekräfta lösenord', validators=[DataRequired('Du måste fylla i ett lösenord.'), EqualTo('password', 'Lösenorden matchar inte.')])
    submit = SubmitField('Återställ lösenord')


class TransferTicketForm(FlaskForm):
    id = HiddenField()
    email = StringField('Mail', validators=[DataRequired('Ange mottagarens mailadress.'), Email('Det där är inte en mailadress.')])
    transfer_submit = SubmitField('Överför biljett')

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Det finns inget konto med den mailadressen. Du måste registrera dig först.')


class SellTicketForm(FlaskForm):
    id = HiddenField()
    sell_submit = SubmitField('Sälj biljett')


class TicketForm(Form):
    meta_id = HiddenField()
    amount = IntegerField('Antal biljetter')

class BuyTicketForm(FlaskForm):
    tickets = FieldList(FormField(TicketForm), min_entries=0, max_entries=20)
    phone = StringField('Telefonnummer')
    submit = SubmitField('Gå till betalning')


class BuyReservedTicketForm(FlaskForm):
    tickets = FieldList(FormField(TicketForm), min_entries=0, max_entries=30)
    phone = StringField('Telefonnummer')
    submit = SubmitField('Gå till betalning')

class ContactForm(FlaskForm):
    name = StringField('Namn', validators=[DataRequired('Vad heter du?'), Length(min=2, max=60)])
    email = StringField('Mailadress', validators=[DataRequired('Vad är din mailadress?'), Email('Det där är inte en mailadress.')])
    topic = TextAreaField('Meddelande',validators=[DataRequired('Vad är ditt meddelande?')])
    submit = SubmitField('Skicka')

