# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 15:43:33
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : config.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_BINDS = {
        'test': 'sqlite:///' + os.path.join(basedir, 'app/static/db/test/test.db')
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # MAIL_SERVER = os.environ.get('MAIL_SERVER')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['1093387079@qq.com', 'fhd573906@gmail.com']
    LANGUAGES = ['zh_CN', 'en', 'es', 'en-US', 'en-GB', 'en-CA']
    POSTS_PER_PAGE = 25

    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    #
    # RECAPTCHA_USE_SSL = False
    # RECAPTCHA_PUBLIC_KEY = 'public'
    # RECAPTCHA_PRIVATE_KEY = 'private'
    # RECAPTCHA_OPTIONS = {'theme': 'white'}

    UPLOAD_FOLDERS = {'registe_manage_app_extension': 'app\\static\\upload\\upload_app_extension',
                      'app_manage_function_configure': 'app\\static\\upload\\upload_conf_app',
                      'app_manage_function_configure_html': '..\\static\\upload\\upload_conf_app',
                      'tenant_service_customize_function': 'app\\static\\upload\\upload_conf_tenant',
                      'tenant_service_customize_function_html': '..\\static\\upload\\upload_conf_tenant',
                      'tenant_service_role_setting': 'app\\static\\upload\\upload_conf_role',
                      'tenant_service_role_setting_html': '..\\static\\upload\\upload_conf_role',
                      }
