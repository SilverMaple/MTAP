# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 15:47:27
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : __init__.py

from flask import Blueprint
from enum import Enum


class LoginType(Enum):
    REGISTE_MANAGE=0
    WEB_APP_MANAGE=1
    TENANT_SERVICE=2

bp = Blueprint('auth', __name__)
current_login_type = LoginType.REGISTE_MANAGE

from app.auth import routes