
import os
import secrets
from PIL import Image
from flask import url_for, current_app
from flask_mail import Message
from qrave import mail


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='MAIL_USERNAME',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


def send_verify_email(user):
    token = user.get_verify_token()
    msg = Message('Verify QRave account',
                  sender='MAIL_USERNAME',
                  recipients=[user.email])
    msg.body = f'''To verify your QRave account, visit the following link:
{url_for('users.verify_account', token=token, _external=True)}
'''
    mail.send(msg)

def send_purchase_email(user,payment):
    ticket_info = ""
    for ticket in payment.tickets:
        ticket_info += ticket.meta.name +" "+ str(ticket.meta.price)+"kr <br>"

    ticket_info += "<br>Totalt pris: "+str(payment.price)+"kr"
    msg = Message('Ditt köp hos QRave',
                  sender='MAIL_USERNAME',
                  recipients=[user.email])
    msg.html = f'''Tack {user.name} för ditt köp hos Qrave! <br><br>

Biljetterna finns nu på ditt konto under <a href='{url_for('users.tickets', _external=True)}'> Mina biljetter</a><br><br>

{ticket_info}<br><br>

Du handlar enbart här för du har inget annat val!<br>
QRam QRave

'''
    mail.send(msg)

def send_contact_email(name,email,topic):
    msg = Message('Kontakt från kund',
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[current_app.config['MAIL_USERNAME']])
    msg.body = f'''Namn: {name}
    Email: {email}
    Medelande: {topic}
    '''
    mail.send(msg)

    