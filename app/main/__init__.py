# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 14:52:16
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : __init__.py.py

from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes