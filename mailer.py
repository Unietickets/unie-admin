from flask import url_for
from flask_mail import Mail
from flask_mail import Message
mail = Mail()

def send_mail(subject, sender, recipients, body):
    msg = Message(subject,sender=sender,recipients=recipients)
    msg.body = f'''{body}'''
    mail.send(msg)

