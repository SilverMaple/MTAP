# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 15:49:27
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : routes.py
import json
import os
import time

from flask import render_template, redirect, url_for, flash, request, session, make_response, current_app
from requests import cookies
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from flask_babel import _
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm, RemoteLoginForm
from app.models import User
from app.auth.email import send_password_reset_email
from app.auth import current_login_type
from app.auth import LoginType
from app import auth
from app.models import SaasRole, SaasUser, SaasMetedataField, SaasRoleToFuncpack


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if auth.current_login_type == LoginType.REGISTE_MANAGE:
            return redirect(url_for('main.index_registe'))
        if auth.current_login_type == LoginType.WEB_APP_MANAGE:
            return redirect(url_for('main.index_app'))
        if auth.current_login_type == LoginType.TENANT_SERVICE:
            return redirect(url_for('main.index_tenant'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # set a debug manage id for test
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))
        init_app_manager()
        init_tenant_service()
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    typeName = None
    if auth.current_login_type == LoginType.REGISTE_MANAGE:
        typeName = 'Registe Manage'
    if auth.current_login_type == LoginType.WEB_APP_MANAGE:
        typeName = 'Web App Manage'
    if auth.current_login_type == LoginType.TENANT_SERVICE:
        typeName = 'Tenant Service'
    return render_template('auth/login.html', title=_('Sign In'), form=form, typeName=typeName)


def init_app_manager():
    session['current_app_manager_id'] = '7'


def init_tenant_service():
    session['current_tenant_id'] = '6'
    SaasRole.__bind_key__ = 'test'
    SaasUser.__bind_key__ = 'test'
    SaasMetedataField.__bind_key__ = 'test'
    SaasRoleToFuncpack.__bind_key__ = 'test'


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('auth.login'))
    typeName = None
    if auth.current_login_type == LoginType.REGISTE_MANAGE:
        typeName = 'Registe Manage'
    if auth.current_login_type == LoginType.WEB_APP_MANAGE:
        typeName = 'Web App Manage'
    if auth.current_login_type == LoginType.TENANT_SERVICE:
        typeName = 'Tenant Service'
    return render_template('auth/register.html', title=_('Register'),
                           form=form, typeName=typeName)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(
            _('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'), form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


# remote login
@bp.route('/remote_login', methods=['GET', 'POST'])
def remote_login():
    form = RemoteLoginForm()
    if form.validate_on_submit():
        # user = User.query.filter_by(username=form.username.data).first()
        # if user is None or not user.check_password(form.password.data):
        #     flash(_('Invalid username or password'))
        #     return redirect(url_for('auth.login'))
        # init_app_manager()
        # init_tenant_service()
        # login_user(user, remember=form.remember_me.data)
        # next_page = request.args.get('next')
        # if not next_page or url_parse(next_page).netloc != '':
        #     next_page = url_for('main.index')
        # return redirect
        # verify code...

        response = current_app.make_response(render_template('index.html'))
        response.set_cookie("saas_appID", form.app_id.data, 86400)
        response.set_cookie("saas_tenantID", form.tenant_id.data, 86400)
        response.set_cookie("saas_userName", form.username.data, 86400)
        response.set_cookie("saas_accessToken", str(time.time()), 86400)
        response.set_cookie("saas_dataSourceFile", './static/TenantDB.json', 86400)
        response.set_cookie("saas_apiAddr", 'http://110.64.91.68:5000', 86400)
        return response
    return render_template('auth/remote_login.html', title=_('Sign In'), form=form)