from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from os.path import basename

import smtplib, ssl

def send_attachment(filename, address):
    msg = MIMEMultipart()
    msg["From"] = "guidescsja@gmail.com"
    msg["To"] = address
    msg["Subject"] = "Guides event ticket"

    with open(filename, "rb") as fil:
        part = MIMEApplication(
            fil.read(),
            Name=basename(filename)
            )
    part["Content-Disposition"] = 'attachment; filename="%s"'%basename(filename)
    msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(msg["From"], "guides@antoura.2022")
        server.sendmail(msg["From"], msg["To"], msg.as_string())


send_attachment("D:/Documents/Certificates/CS50x.pdf", "charbelhannoun63@gmail.com")
