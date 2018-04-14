# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 15:47:33
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : email.py

from app.decorators import async
from threading import Thread
from flask import render_template
from flask_mail import Message
from app import mail, current_app
from flask_babel import _

@async
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Thread(target=send_async_email, args=(app, msg)).start()
    send_async_email(current_app._get_current_object(), msg)


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(_('[MoodBit] Reset Your Password'),
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))

def follower_notification(followed, follower):
    send_email(_("[MoodBit] %{username}s is now following you!", username=follower.username),
               current_app.config['ADMINS'][0],
               [followed.email],
               render_template('email/follower_email.txt',
                               user=followed, follower=follower),
               render_template('email/follower_email.html',
                               user=followed, follower=follower))