# Detta är vårt kandidatarbete :smiley:

#### Installera

1. Skapa en mapp där ni vill clona repot.
2. cd till mappen.
3. `git clone git@gitlab.liu.se:davfo018/tddd83.git`
4. `python3 -m venv venv`
5. `. venv/bin/activate`
6. `pip install -r requirements.txt`
7. Öppna VSCode, tryck CMD + SHIFT + P.
8. Skriv PATH och välj: 'Shell Command: Install 'code' command in PATH'
9. Stäng VScode. I terminalen skriv: `chmod u+x ./install_alias.sh`
10. Sedan: `./install_alias.sh`
11. Stäng terminalen med CMD + Q, och öppna den på nytt.
12. Skriv `kand` i terminalen och se magi!

Har man windows så får man kämpa :unamused:

#### Flask helpers

I [flask_helpers](qrave/flask_helpers.py) finns ett antal hjälpfunktioner. För att använda dessa skriver man i terminalen:
    
    flask helpers <COMMAND>
    Exempelvis:
    flask helpers resetDB

#### QR JS API:er
1. Scanner: [instascan](https://github.com/schmich/instascan)
2. Generator: [EasyQRCodeJS](https://www.npmjs.com/package/easyqrcodejs)

#### Början på en filstruktur 

    ├── README.md
    ├── requirements.txt
    ├── run.py
    └── qrave
        ├── init.py
        ├── config.py
        ├── models.py
        ├── flaks_helpers.py
        ├── errors
        │   ├── init.py
        │   └── handlers.py
        ├── main
        │   ├── init.py
        │   └── routes.py
        ├── users
        │   ├── init.py
        │   ├── routes.py
        │   ├── forms.py
        │   └── utils.py
        ├── static
        │   └── site.css
        └── templates
            ├── layout.html
            ├── errors
            │   ├── 403.html
            │   ├── 404.html
            │   └── 500.html
            ├── main
            │   ├── events.html
            │   └── home.html
            └── users
                ├── account.html
                ├── login.html
                ├── register.html
                ├── reset_request.html
                └── reset_token.html
        
            
