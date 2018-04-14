# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 13:41:50
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : __init__.py

from flask import Blueprint

bp = Blueprint('errors', __name__)

from app.errors import handlers