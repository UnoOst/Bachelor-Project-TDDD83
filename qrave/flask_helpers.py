from flask import Flask, current_app
from flask.cli import AppGroup

from qrave import bcrypt, db, models

from .models import *
from datetime import datetime

helper = AppGroup('helpers')


@helper.command('seedDB')
def seedDB():
    role = Roles(name="admin")
    cm = Hosts(long_name="Clubmästeriet", short_name="CM", description="Clubmästeriet är mästeriet på sektionen för Industriell Ekonomi vid Linköpings Universitet och grundades samma år som sektionen själv, 1969. Ett mästeri är en förening som är både ett fadderi och ett festeri. Ett fadderi är den förening på varje sektion som arrangerar mottagningsperioden för de nya studenterna som varje år börjar på universitetet. Ett festeri är den förening på varje sektion som arrangerar fester och andra arrangemang för såväl den egna sektionen som resterande universitetet.", image='images/defaulthost.jpg')
    fm = Hosts(long_name="Festmaskineriet", short_name="FM", description="Maskinteknologsektionens fantastiska festeri. Festmaskineriet berättar vad som händer! Och vad som hände... <a href='www.festmaskineriet.com'>www.festmaskineriet.com</a>", image='images/fm.png')
    elin = Hosts(long_name="Ekonomföreningen vid Linköpings universitet", short_name="Elin", description="ELIN är en ideell förening som startade 1971 och har idag drygt 1000 medlemmar, vilket gör oss till en av Linköpings största studentföreningar. Vi intresserar oss för allt som rör utbildning, näringsliv och det studiesociala för studenter med koppling till civilekonomprogrammet vid Linköpings universitet. Vi jobbar dessutom ständigt för att på ett professionellt sätt utveckla både utbildningen och studiernas förankring till arbetslivet. <a href='www.elin.se'>www.elin.se</a>", image='images/elin.png')

    usr = Users(name="Liu ID", email="liuid123@student.liu.se", phone="0707885901", liuid="liuid123", is_verified=True)
    usr1 = Users(name="David Forslöf", email="davfo018@student.liu.se", phone="0707885901", liuid="davfo018", is_verified=True)
    usr2 = Users(name="Uno Österman", email="unoos123@student.liu.se", phone="0707885901", liuid="unoos123", is_verified=True)
    usr3 = Users(name="Oskar Lindström", email="oskli548@student.liu.se", phone="0707885901", liuid="oskli548", is_verified=True)
    usr4 = Users(name="Filip Nyberg", email="filny703@student.liu.se", phone="0739435542", liuid="filny703", is_verified=True)
    usr5 = Users(name="Jesper Carlsson", email="jesca143@student.liu.se", phone="0707885901", liuid="jesca143", is_verified=True)
    usr6 = Users(name="Jesper Jissbakcke", email="jesji843@student.liu.se", phone="0707885901", liuid="jesji843", is_verified=True)
    usr7 = Users(name="Agnes Öberg", email="agnob120@student.liu.se", phone="0707885901", liuid="agnob120", is_verified=True)
    usr8 = Users(name="Emil Strömberg", email="emist981@student.liu.se", phone="0707885901", liuid="emist981", is_verified=True)
    usr.set_password("123123")
    usr1.set_password("123123")
    usr2.set_password("123123")
    usr3.set_password("123123")
    usr4.set_password("123123")
    usr5.set_password("123123")
    usr6.set_password("123123")
    usr7.set_password("123123")
    usr8.set_password("123123")
    usr.hosts.append(cm)
    
    admin = Users(name="admin", email="admin@admin.se", phone="123123", is_verified=True)
    admin.set_password("admin")
    admin.roles.append(role)

    uk = Events(name="Utekravallen", description="UK", date_start=datetime.strptime("2020-05-15", '%Y-%m-%d'), date_end=datetime.strptime("2020-05-17", '%Y-%m-%d'),
                date_publication=datetime.strptime("2020-04-23", '%Y-%m-%d'), date_ticket_sale=datetime.strptime("2020-04-22", '%Y-%m-%d'), ticket_location="U11")
    uk.host = cm
    märke = Products(name="UK märke", description="Vårat UK märke", price=20, capacity=4000)
    neonband = Products(name="Neonband", description="Neonband i olika färger", price=20, capacity=200)
    uk.products.append(märke)
    uk.products.append(neonband)
    
    draget = Events(name="Dra't i Spa't", description="Draget", date_start=datetime.strptime("2020-09-18", '%Y-%m-%d'), date_end=datetime.strptime("2020-09-20", '%Y-%m-%d'),
                date_publication=datetime.strptime("2020-04-23", '%Y-%m-%d'), date_ticket_sale=datetime.strptime("2020-09-18", '%Y-%m-%d'), ticket_location="Kårallen", image="images/Draget.jpg")
    draget.host = cm

    biljett = TicketMeta(name="UK Biljett", price=140, capacity=1000, location="Kårallen",
                         max_per_user=4, date_start=datetime.strptime("2020-05-15", '%Y-%m-%d'), date_end=datetime.strptime("2020-05-16", '%Y-%m-%d'), image="images/UK_biljett.jpg")
    biljett.event = uk
    
    dragetbiljett = TicketMeta(name="Draget Biljett", price=140, capacity=2000, location="Tinnerbäcken",
                         max_per_user=4, date_start=datetime.strptime("2020-09-18", '%Y-%m-%d'), date_end=datetime.strptime("2020-09-19", '%Y-%m-%d'))
    dragetbiljett.event = draget

    db.session.add_all([usr, usr1, usr2,usr3,usr4,usr5,usr6,usr7,usr8, role, cm, uk, biljett, neonband, märke, admin, draget, dragetbiljett, elin, fm])
    db.session.commit()

    #om jag vill lägga till något mer, lägg till ovan

    biljett.generate_tickets()
    dragetbiljett.generate_tickets()
    
    ticket = uk.ticket_meta[0].get_first_free_ticket()
    ticket.transfer_ticket(usr.id)

    ticket_draget = draget.ticket_meta[0].get_first_free_ticket()
    ticket_draget.transfer_ticket(usr.id)

    db.session.commit()

    print("done")


@helper.command('resetDB')
def resetDB():
    db.drop_all()
    db.create_all()
    print("done")
