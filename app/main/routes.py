# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 14:53:17
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : routes.py

import hashlib
import os
import logging
import sys
import shutil
import json
import subprocess
import time
from datetime import datetime

from app.decorators import async
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app, session, make_response
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from flask_uploads import UploadSet
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, PostForm, SearchForm, AddAppForm, AddAppExtensionForm, EditAppExtensionForm, \
    AddAppAdminForm, AddTenantForm, AddTenantDatabaseForm, EditTenantDatabaseForm, AddAppCodeForm, AddRoleForm, AddUserForm
from app.models import User, Post, App, AppAdmin, AppExpand, AdminToApp, Tenant, TenantDb, AppCode, SaasRole, SaasUser
from app.translate import translate
from app.main import bp
from app.email import follower_notification
from app.auth import LoginType, current_login_type
from app import auth
from pip._internal import commands
from requests import Response
from werkzeug.datastructures import FileStorage
from werkzeug.test import EnvironBuilder
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

logger = logging.getLogger("MirrorConstruct")
# logger = logging.getLogger("MirrorConstruct")
formatter = logging.Formatter('[%(asctime)s]  %(message)s')
blank_formatter = logging.Formatter('')
# formatter = logging.Formatter('[%(asctime)s][%(levelname)s] ## %(message)s')
file_handler = logging.FileHandler("logs/mirror_construct.log")
file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式

# 为logger添加的日志处理器
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/index_registe')
def index_registe():
    if current_user.is_authenticated and auth.current_login_type == LoginType.REGISTE_MANAGE:
        return render_template('index_registe_manage.html', title=_('Registe Manage'))
    else:
        auth.current_login_type = LoginType.REGISTE_MANAGE
        return redirect(url_for('auth.login'))


@bp.route('/index_app')
def index_app():
    if current_user.is_authenticated and auth.current_login_type == LoginType.WEB_APP_MANAGE:
        app_list = [a.app_id for a in AdminToApp.query.filter(
            AdminToApp.app_admin_id == session['current_app_manager_id']).all()]
        data = [App.query.filter(App.id == a).order_by(db.asc(App.name)).first() for a in app_list]
        data.sort(key=lambda a: a.name)
        app_name_list = [a.name for a in data]
        current_selected_app_name = None
        if session.get('current_selected_app_name'):
            current_selected_app_name = session['current_selected_app_name']
        return render_template('index_app_manage.html', title=_('Web App Manage'), app_name_list=app_name_list,
                               current_selected_app_name=current_selected_app_name)
    else:
        auth.current_login_type = LoginType.WEB_APP_MANAGE
        return redirect(url_for('auth.login'))


@bp.route('/index_tenant')
def index_tenant():
    if current_user.is_authenticated and auth.current_login_type == LoginType.TENANT_SERVICE:
        return render_template('index_tenant_service.html', title=_('Tenant Service'))
    else:
        auth.current_login_type = LoginType.TENANT_SERVICE
        return redirect(url_for('auth.login'))


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s!', username=username))
    follower_notification(user, current_user)
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


# ---------------------------------------------------------------------------------------
# registe manage app setting
# ---------------------------------------------------------------------------------------
@bp.route('/registe_manage_app_setting')
@login_required
def registe_manage_app_setting():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.order_by(db.asc(App.name)).all()
    return render_template('registe_manage_app_setting.html', title=_('App Setting'),
                           tableName=_('App List'), AppAdmin=AppAdmin,
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/registe_manage_app_setting_add', methods=['GET', 'POST'])
@login_required
def registe_manage_app_setting_add():
    form = AddAppForm(None)
    if form.validate_on_submit():
        app_id = hashlib.md5(form.app_name.data.encode(encoding='UTF-8')).hexdigest()
        db.session.add(App(id=None, name=form.app_name.data, appid=app_id))
        db.session.commit()
        flash(_('New app have been added.'))
        return redirect(url_for('main.registe_manage_app_setting'))
    elif request.method == 'GET':
        pass
    return render_template('registe_manage_app_setting.html', title=_('App Setting'),
                           tableName=_('Add New App'), AppAdmin=AppAdmin, form=form,
                           addTitle=('Add New App'))


@bp.route('/registe_manage_app_setting_delete/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_setting_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = App.query.filter(App.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('registe_manage_app_setting.html', title=_('App Setting'),
                           tableName=_('App List'), AppAdmin=AppAdmin,
                           isCheck=isCheck, isEdit=isEdit, session=session,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/registe_manage_app_setting_delete_select', methods=['GET', 'POST'])
@login_required
def registe_manage_app_setting_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.registe_manage_app_setting'))


@bp.route('/registe_manage_app_setting_edit/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_setting_edit(id):
    if session.get('validate_app_name'):
        form = AddAppForm(session['validate_app_name'])
    else:
        form = AddAppForm(None)
    if form.validate_on_submit():
        current_data = App.query.filter(App.id == id).first()
        current_data.name = form.app_name.data
        db.session.commit()
        flash(_('App have been edited.'))
        return redirect(url_for('main.registe_manage_app_setting'))
    elif request.method == 'GET':
        current_data = App.query.filter(App.id == id).first()
        form.app_name.data = current_data.name
        form.app_ID.data = current_data.appid
        if AppAdmin.query.filter(AppAdmin.id == current_data.creater_id).first():
            form.creator_name.data = AppAdmin.query.filter(AppAdmin.id == current_data.creater_id).first().name
        session['validate_app_name'] = form.app_name.data
    return render_template('registe_manage_app_setting.html', title=_('App Setting'),
                           tableName=_('Edit App'), AppAdmin=AppAdmin, form=form,
                           editTitle=('Edit App'))


# ---------------------------------------------------------------------------------------
# registe manage app extension
# ---------------------------------------------------------------------------------------
@bp.route('/registe_manage_app_extension')
@login_required
def registe_manage_app_extension():
    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Type'), _('Tag Template/Begin'), _('Tag Template/End'), _('Library File'), _('DB Initial Path')]
    data = AppExpand.query.order_by(db.asc(AppExpand.type)).all()
    return render_template('registe_manage_app_extension.html', title=_('App Extension'),
                           tableName=_('App Extension List'),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/registe_manage_app_extension_add', methods=['GET', 'POST'])
@login_required
def registe_manage_app_extension_add():
    form = AddAppExtensionForm(None)
    if form.validate_on_submit():
        upload = UploadSet()
        if hasattr(form.library_file.data, 'filename'):
            filename1 = secure_filename(form.library_file.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['registe_manage_app_extension'],
                                                  'library'), filename1).replace('\\', '/')
            form.library_file.data.save(filePath1)
        else:
            filePath1=''
        if hasattr(form.library_file_depend.data, 'filename'):
            filename2 = secure_filename(form.library_file_depend.data.filename)
            filePath2 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['registe_manage_app_extension'],
                                                  'library_depend'), filename2).replace('\\', '/')
            form.library_file_depend.data.save(filePath2)
        else:
            filePath2 = ''

        db.session.add(AppExpand(id=None, type=form.app_type.data, pattern_begin=form.tag_begin.data,
                                 pattern_end=form.tag_end.data, library_path=filePath1,
                                 library_depend_path=filePath2,
                                 library_desc=form.library_file_description.data,
                                 db_init_path=form.db_info_file_path.data))
        db.session.commit()
        flash(_('New app extension have been added.'))
        return redirect(url_for('main.registe_manage_app_extension'))
    elif request.method == 'GET':
        pass
    return render_template('registe_manage_app_extension.html', title=_('App Extension'),
                           tableName=_('Add New App Extension'), AppAdmin=AppAdmin, form=form,
                           addTitle=('Add New App Extension'))


@bp.route('/registe_manage_app_extension_delete/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_extension_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = AppExpand.query.filter(AppExpand.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Type'), _('Tag Template/Begin'), _('Tag Template/End'), _('Library File'), _('DB Initial Path')]
    data = AppExpand.query.all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('registe_manage_app_extension.html', title=_('App Extension'),
                           tableName=_('App Extension List'),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/registe_manage_app_extension_delete_select', methods=['GET', 'POST'])
@login_required
def registe_manage_app_extension_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.registe_manage_app_extension'))


@bp.route('/registe_manage_app_extension_edit/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_extension_edit(id):
    if session.get('validate_app_type'):
        form = EditAppExtensionForm(session['validate_app_type'])
    else:
        form = EditAppExtensionForm(None)

    if form.validate_on_submit():
        current_data = AppExpand.query.filter(AppExpand.id == id).first()
        current_data.type = form.app_type.data
        current_data.pattern_begin = form.tag_begin.data
        current_data.pattern_end = form.tag_end.data
        current_data.library_desc = form.library_file_description.data
        current_data.db_init_path = form.db_info_file_path.data
        # print(form.library_file.data == '')
        # print(form.library_file.data)
        form.library_file.description = _('Selected File: ') + os.path.basename(current_data.library_path)
        form.library_file_depend.description = _('Selected File: ') + os.path.basename(current_data.library_depend_path)

        if hasattr(form.library_file.data, 'filename'):
            filename1 = secure_filename(form.library_file.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['registe_manage_app_extension'],
                                                  'library'), filename1).replace('\\', '/')
            form.library_file.data.save(filePath1)
            current_data.library_path = filePath1
        if hasattr(form.library_file_depend.data, 'filename'):
            filename2 = secure_filename(form.library_file_depend.data.filename)
            filePath2 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['registe_manage_app_extension'],
                                                  'library_depend'), filename2).replace('\\', '/')
            form.library_file_depend.data.save(filePath2)
            current_data.library_depend_path = filePath2

        db.session.commit()
        flash(_('App have been edited.'))
        return redirect(url_for('main.registe_manage_app_extension'))
    elif request.method == 'GET':
        current_data = AppExpand.query.filter(AppExpand.id == id).first()
        form.app_type.data =current_data.type
        form.tag_begin.data = current_data.pattern_begin
        form.tag_end.data = current_data.pattern_end
        form.library_file.description = _('Selected File: ') + os.path.basename(current_data.library_path)
        form.library_file_depend.description = _('Selected File: ') + os.path.basename(current_data.library_depend_path)
        form.library_file_description.data = current_data.library_desc
        form.db_info_file_path.data = current_data.db_init_path
        session['validate_app_type'] = form.app_type.data
    return render_template('registe_manage_app_extension.html', title=_('App Extension'),
                           tableName=_('Edit App Extension'), AppAdmin=AppAdmin, form=form,
                           editTitle=('Edit App Extension'))


# ---------------------------------------------------------------------------------------
# registe manage app manager setting
# ---------------------------------------------------------------------------------------
@bp.route('/registe_manage_app_manager_setting')
@login_required
def registe_manage_app_manager_setting():
    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Manager Name'), _('App Name')]
    data = {}

    preData = AppAdmin.query.all()
    for p in preData:
        managerName = p.name
        for temp in AdminToApp.query.filter(AdminToApp.app_admin_id == p.id):
            appName = App.query.filter(App.id == temp.app_id).first().name
            if data.get(managerName):
                data[managerName]['name'].append(appName)
            else:
                data[managerName] = {}
                data[managerName]['id'] = p.id
                data[managerName]['name'] = []
                data[managerName]['name'].append(appName)
        if not data.get(managerName):
            data[managerName] = {}
            data[managerName]['id'] = p.id
            data[managerName]['name'] = ''
        else:
            data[managerName]['name'].sort()
            data[managerName]['name'] = '; '.join(data[managerName]['name'])
    data['sort'] = list(data.keys())
    data['sort'].sort()
    return render_template('registe_manage_app_manager_setting.html', title=_('App Manager Setting'),
                           tableName=_('App Manager List'),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/registe_manage_app_manager_setting_add', methods=['GET', 'POST'])
@login_required
def registe_manage_app_manager_setting_add():
    form = AddAppAdminForm(None)
    if form.validate_on_submit():
        db.session.add(AppAdmin(id=None, name=form.app_admin_name.data,
                                password=generate_password_hash(form.app_admin_password.data)))
        db.session.commit()
        app_admin_id = AppAdmin.query.filter(AppAdmin.name == form.app_admin_name.data).first().id
        for app_name in form.app_list.data:
            app_id = App.query.filter(App.name == app_name).first().id
            db.session.add(AdminToApp(id=None, app_admin_id=app_admin_id, app_id=app_id))
        db.session.commit()
        flash(_('New app manager have been added.'))
        return redirect(url_for('main.registe_manage_app_manager_setting'))
    elif request.method == 'GET':
        pass
    return render_template('registe_manage_app_manager_setting.html', title=_('App Manager Setting'),
                           tableName=_('Add New App Manager'), AppAdmin=AppAdmin, form=form,
                           addTitle=('Add New App Manager'))


@bp.route('/registe_manage_app_manager_setting_delete/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_manager_setting_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = AppAdmin.query.filter(AppAdmin.id == session['current_delete_id']).first()
            for removeAdminToApp in AdminToApp.query.filter(AdminToApp.app_admin_id==current_data.id).all():
                db.session.delete(removeAdminToApp)
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Manager Name'), _('App Name')]
    data = {}

    preData = AppAdmin.query.all()
    for p in preData:
        managerName = p.name
        for temp in AdminToApp.query.filter(AdminToApp.app_admin_id == p.id):
            appName = App.query.filter(App.id == temp.app_id).first().name
            if data.get(managerName):
                data[managerName]['name'].append(appName)
            else:
                data[managerName] = {}
                data[managerName]['id'] = p.id
                data[managerName]['name'] = []
                data[managerName]['name'].append(appName)
        if not data.get(managerName):
            data[managerName] = {}
            data[managerName]['id'] = p.id
            data[managerName]['name'] = ''
        else:
            data[managerName]['name'].sort()
            data[managerName]['name'] = '; '.join(data[managerName]['name'])
    data['sort'] = list(data.keys())
    data['sort'].sort()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('registe_manage_app_manager_setting.html', title=_('App Manager Setting'),
                           tableName=_('App Manager List'),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/registe_manage_app_manager_setting_delete_select', methods=['GET', 'POST'])
@login_required
def registe_manage_app_manager_setting_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.registe_manage_app_manager_setting'))


@bp.route('/registe_manage_app_manager_setting_edit/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_manager_setting_edit(id):
    if session.get('validate_app_admin_name'):
        form = AddAppAdminForm(session['validate_app_admin_name'])
    else:
        form = AddAppAdminForm(None)
    if form.validate_on_submit():
        old_app_list = session['old_app_list'] if session.get('old_app_list') else []
        new_app_list = form.app_list.data
        add_app_list = [a for a in new_app_list if a not in old_app_list]
        remove_app_list = [a for a in old_app_list if a not in new_app_list]
        current_data = AppAdmin.query.filter(AppAdmin.id == id).first()
        current_data.name = form.app_admin_name.data
        if not form.app_admin_password.data.strip() == '':
            current_data.password = generate_password_hash(form.app_admin_password.data)
        for a in add_app_list:
            add_app_id = App.query.filter(App.name == a).first().id
            db.session.add(AdminToApp(id=None, app_admin_id=id, app_id=add_app_id))
        for a in remove_app_list:
            remove_app_id = App.query.filter(App.name == a).first().id
            removeAdminToApp = AdminToApp.query.filter(AdminToApp.app_admin_id==id, AdminToApp.app_id==remove_app_id).first()
            db.session.delete(removeAdminToApp)
        db.session.commit()
        flash(_('App Admin have been edited.'))
        return redirect(url_for('main.registe_manage_app_manager_setting'))
    elif request.method == 'GET':
        current_data = AppAdmin.query.filter(AppAdmin.id == id).first()
        app_list = [a.app_id for a in AdminToApp.query.filter(AdminToApp.app_admin_id == id)]
        app_name_list = [App.query.filter(App.id == a).first().name for a in app_list]
        form.app_admin_name.data = current_data.name
        form.app_list.data = app_name_list
        session['validate_app_admin_name'] = form.app_admin_name.data
        session['old_app_list'] = app_name_list
    return render_template('registe_manage_app_manager_setting.html', title=_('App Manager Setting'),
                           tableName=_('Edit App Manager'), AppAdmin=AppAdmin, form=form,
                           editTitle=('Edit App Manager'))


# ---------------------------------------------------------------------------------------
# registe manage app tenant setting
# ---------------------------------------------------------------------------------------
@bp.route('/registe_manage_app_tenant_setting')
@login_required
def registe_manage_app_tenant_setting():
    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Tenant Name'), _('App Tenant ID'), _('App Name')]
    data = Tenant.query.order_by(db.asc(Tenant.name)).all()
    return render_template('registe_manage_app_tenant_setting.html', title=_('App Tenant Setting'),
                           tableName=_('App Tenant List'), App=App,
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/registe_manage_app_tenant_setting_add', methods=['GET', 'POST'])
@login_required
def registe_manage_app_tenant_setting_add():
    form = AddTenantForm(None)
    if form.validate_on_submit():
        app_id = App.query.filter(App.name == form.app_list.data).first().id
        db.session.add(Tenant(id=None, name=form.tenant_name.data,
                                password=generate_password_hash(form.tenant_password.data),
                                tenantid=hashlib.md5(form.tenant_name.data.encode(encoding='UTF-8')).hexdigest(),
                                app_id=app_id))
        db.session.commit()
        flash(_('New Tenant have been added.'))
        return redirect(url_for('main.registe_manage_app_tenant_setting'))
    elif request.method == 'GET':
        pass
    return render_template('registe_manage_app_tenant_setting.html', title=_('App Tenant Setting'),
                           tableName=_('Add New App Tenant'), form=form,
                           addTitle=('Add New App Tenant'))


@bp.route('/registe_manage_app_tenant_setting_delete/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_tenant_setting_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = Tenant.query.filter(Tenant.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    tHead = [_('App Tenant Name'), _('App Tenant ID'), _('App Name')]
    data = Tenant.query.order_by(db.asc(Tenant.name)).all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('registe_manage_app_tenant_setting.html', title=_('App Tenant Setting'),
                           tableName=_('App Tenant List'), App=App,
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)

@bp.route('/registe_manage_app_tenant_setting_delete_select', methods=['GET', 'POST'])
@login_required
def registe_manage_app_tenant_setting_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.registe_manage_app_manager_setting'))


@bp.route('/registe_manage_app_tenant_setting_edit/<id>', methods=['GET', 'POST'])
@login_required
def registe_manage_app_tenant_setting_edit(id):
    if session.get('validate_app_tenant_name'):
        form = AddTenantForm(session['validate_app_tenant_name'])
    else:
        form = AddTenantForm(None)
    if form.validate_on_submit():
        current_data = Tenant.query.filter(Tenant.id == id).first()
        current_data.name = form.tenant_name.data
        if not form.tenant_password.data.strip() == '':
            current_data.password = generate_password_hash(form.tenant_password.data)
        app_id = App.query.filter(App.name == form.app_list.data).first().id
        current_data.app_id = app_id
        db.session.commit()
        flash(_('App Tenant have been edited.'))
        return redirect(url_for('main.registe_manage_app_tenant_setting'))
    elif request.method == 'GET':
        current_data = Tenant.query.filter(Tenant.id == id).first()
        app_name =  App.query.filter(App.id == current_data.app_id).first().name
        form.tenant_name.data = current_data.name
        form.app_list.data = app_name
        form.tenant_id.data = current_data.tenantid
        session['validate_app_tenant_name'] = form.tenant_name.data
    return render_template('registe_manage_app_tenant_setting.html', title=_('App Tenant Setting'),
                           tableName=_('Edit App Tenant'), form=form,
                           editTitle=('Edit App Tenant'))


# ---------------------------------------------------------------------------------------
# app manage change current app
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_set_current_app', methods=['GET', 'POST'])
@login_required
def app_manage_set_current_app():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        current_data = App.query.filter(App.name == name).first()
        if current_data:
            session['current_selected_app_id'] = current_data.id
            session['current_selected_app_name'] = current_data.name
            flash(_('Switch current app success!'))
            return jsonify({'result': 'success'})


def get_app_name_list():
    app_list = [a.app_id for a in AdminToApp.query.filter(
        AdminToApp.app_admin_id == session['current_app_manager_id']).all()]
    data = [App.query.filter(App.id == a).order_by(db.asc(App.name)).first() for a in app_list]
    data.sort(key=lambda a: a.name)
    app_name_list = [a.name for a in data]
    return app_name_list


def get_current_selected_app_name():
    current_selected_app_name = None
    if session.get('current_selected_app_name'):
        current_selected_app_name = session['current_selected_app_name']
    return current_selected_app_name


# ---------------------------------------------------------------------------------------
# app manage app list
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_app_list')
@login_required
def app_manage_app_list():
    isCheck = True
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    app_list = [ a.app_id for a in AdminToApp.query.filter(
        AdminToApp.app_admin_id == session['current_app_manager_id']).all()]
    data = [ App.query.filter(App.id == a).order_by(db.asc(App.name)).first() for a in app_list]
    data.sort(key=lambda a: a.name)
    return render_template('app_manage_app_list.html', title=_('App List'),
                           tableName=_('App List'), AppAdmin=AppAdmin, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, tHead=tHead, data=data)


# ---------------------------------------------------------------------------------------
# app manage code configure
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_function_configure')
@login_required
def app_manage_function_configure():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.order_by(db.asc(App.name)).all()
    return render_template('app_manage_function_configure.html', title=_('Online Function'),
                           tableName=_('Function Configure'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/app_manage_function_configure_test')
@login_required
def app_manage_function_configure_test():
    testFunc()
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.order_by(db.asc(App.name)).all()
    return render_template('app_manage_function_configure.html', title=_('Online Function'),
                           tableName=_('Function Configure'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


def testFunc():
    filePath = 'F:/test/main.html'
    pattern = 'x;/<dd>.*API监控.*<\/dd>/{p;q};/<dd>.*<\/dd>/{x;h;d;ta};/<dd>.*/{x;H;ta};{x;h;d};:a'
    tag_begin = '{if .role_APIguanli}'
    tag_end = '{end}'
    args = 'cat -n %s | sed -n "%s" | { eval $(awk \'NR==1{print "a="$1} END {print "b="$1}\'); ' \
           'sed -e "$a i %s" -e "$b a %s" %s;} > F:/test/test.txt' % (filePath, pattern, tag_begin, tag_end, filePath)
    shell_file = open('F:/test/temp.sh', 'w', encoding='utf-8')
    shell_file.write(args)
    shell_file.flush()
    shell_file.close()
    exec_path = "D:\Program Files\Git\git-bash.exe"
    print(args)
    (status, output) = subprocess.getstatusoutput([exec_path, 'F:/test/temp.sh'])
    print(status, output)


@bp.route('/get_file_path/<tag>', methods=['GET', 'POST'])
@login_required
def get_file_path(tag):
    app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
    if tag == 'version2package.json' or tag == 'package2function.json':
        filePath = os.path.join(os.path.join(
            current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id), tag)
        if os.path.isfile(filePath):
            filePath = os.path.join(os.path.join(
                current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure_html'], app_id), tag)
            return jsonify({'result': 'success', 'filePath': filePath})
    return jsonify({'result': 'fail', 'filePath': False})


@bp.route('/app_manage_init_file/<tag>', methods=['GET', 'POST'])
@login_required
def app_manage_init_file(tag):
    app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
    filePath = os.path.join(
        current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id)
    if not os.path.isdir(filePath):
        os.makedirs(filePath)

    initJson = [
        {
            "data": {
                "file_path": "",
                "item_pattern": ""
            },
            "id": "Root",
            "parent": "#",
            "text": "Root"
        }
    ]
    if tag in ['version2package.json', 'package2function.json']:
        try:
            new_file = open(os.path.join(filePath, tag), 'w')
            new_file.write(json.dumps(initJson))
            new_file.close()
            flash(_('File initial for %(tag)s success.', tag=tag))
        except Exception as e:
            print(e)
            flash(_('File initial for %(tag)s failed.', tag=tag))
    return jsonify({'result': 'success'})


@bp.route('/app_manage_save_file', methods=['GET', 'POST'])
@login_required
def app_manage_save_file():
    data = request.get_json()
    app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
    filePath = os.path.join(
        current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id)

    if not os.path.isdir(filePath):
        os.makedirs(filePath)

    tag = data['tag']
    new_json = json.loads(data['json'])
    print(new_json)
    if tag in ['version2package.json', 'package2function.json']:
        try:
            new_file = open(os.path.join(filePath, tag), 'w')
            # new_file.write(json.dumps(new_json))
            # json.dump(new_json, new_file, ensure_ascii=False, indent=4)
            json.dump(new_json, new_file, indent=4)
            new_file.close()
            flash(_('File save for %(tag)s success.', tag=tag))
        except Exception as e:
            print(e)
            flash(_('File save for %(tag)s failed.', tag=tag))
    return jsonify({'result': 'success'})


@bp.route('/app_manage_upload_file', methods=['GET', 'POST'])
@login_required
def app_manage_upload_file():
    version_to_package_file = request.files['version_to_package_file']
    package_to_function_file = request.files['package_to_function_file']
    app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
    filePath = os.path.join(
        current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id)

    if not os.path.isdir(filePath):
        os.makedirs(filePath)
    version_to_package_file.save(os.path.join(filePath, 'version2package.json'))
    package_to_function_file.save(os.path.join(filePath, 'package2function.json'))
    flash(_('Import success!'))
    return jsonify({'result': 'success'})


# ---------------------------------------------------------------------------------------
# app manage database configure
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_database_configure')
@login_required
def app_manage_database_configure():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Tenant'), _('Is System Extension'), _('Database'), _('IP'), _('Port')]
    data = TenantDb.query.filter(TenantDb.app_id == session['current_selected_app_id']).order_by(db.asc(TenantDb.database)).all()
    return render_template('app_manage_database_configure.html', title=_('Tenant Database List'),
                           tableName=_('Tenant Database List'), Tenant=Tenant, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/app_manage_database_configure_add', methods=['GET', 'POST'])
@login_required
def app_manage_database_configure_add():
    form = AddTenantDatabaseForm(None)
    if form.validate_on_submit():
        current_tenant_id = Tenant.query.filter(Tenant.name == form.tenant_name.data).first().id
        current_type = 'system' if form.system_extension.data == 'System Extension' else 'origin'
        db.session.add(TenantDb(id=None, hostname=form.host_name.data, driver=form.database_driver.data,
                                username=form.user_name.data,
                                password=generate_password_hash(form.user_password.data),
                                database=form.database_name.data, port=form.database_port.data,
                                aliasname='_'.join([form.database_driver.data, form.database_name.data]),
                                type=current_type, tenant_id=current_tenant_id, app_id=session['current_selected_app_id']))
        db.session.commit()
        flash(_('New tenant database have been added.'))
        return redirect(url_for('main.app_manage_database_configure'))
    elif request.method == 'GET':
        form.app_name.data = session['current_selected_app_name']
        form.host_name.data = 'localhost'
        form.database_port.data = '3306'
        form.database_driver.data = 'mysql'
        form.user_name.data = 'root'
        pass
    return render_template('app_manage_database_configure.html', title=_('Tenant Database Configure'),
                           tableName=_('Add New Tenant Database'), form=form, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           addTitle=('Add New Tenant Database'))


@bp.route('/app_manage_database_configure_delete/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_database_configure_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = TenantDb.query.filter(TenantDb.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Tenant'), _('Is System Extension'), _('Database'), _('IP'), _('Port')]
    data = TenantDb.query.filter(TenantDb.app_id == session['current_selected_app_id']).order_by(
        db.asc(TenantDb.username)).all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('app_manage_database_configure.html', title=_('Tenant Database List'),
                           tableName=_('Tenant Database List'), Tenant=Tenant, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/app_manage_database_configure_delete_select', methods=['GET', 'POST'])
@login_required
def app_manage_database_configure_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.app_manage_database_configure'))


@bp.route('/app_manage_database_configure_edit/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_database_configure_edit(id):
    if session.get('validate_alias_name'):
        form = EditTenantDatabaseForm(session['validate_alias_name'])
    else:
        form = EditTenantDatabaseForm(None)
    if form.validate_on_submit():
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        current_data.hostname = form.host_name.data
        current_data.driver = form.database_driver.data
        current_data.username = form.user_name.data
        current_data.database = form.database_name.data
        current_data.port = form.database_port.data
        current_data.aliasname = '_'.join([form.database_driver.data, form.database_name.data])
        current_data.type = 'system' if form.system_extension.data == 'System Extension' else 'origin'
        current_data.tenant_id = Tenant.query.filter(Tenant.name == form.tenant_name.data).first().id
        current_data.app_id = session['current_selected_app_id']
        if not form.user_password.data.strip() == '':
            current_data.password = generate_password_hash(form.user_password.data)
        db.session.commit()
        flash(_('Tenant Database have been edited.'))
        return redirect(url_for('main.app_manage_database_configure'))
    elif request.method == 'GET':
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        form.app_name.data = session['current_selected_app_name']
        form.host_name.data = current_data.hostname
        form.database_port.data = current_data.port
        form.system_extension.data = 'System Extension' if current_data.type == 'system' else 'Not System Extension'
        form.database_driver.data = current_data.driver
        form.database_name.data = current_data.database
        form.user_name.data = current_data.username
        form.user_password.description = 'In edit mode, set null in this field means no modification for current password.'
        session['validate_alias_name'] = '_'.join([form.database_driver.data, form.database_name.data])
    return render_template('app_manage_database_configure.html', title=_('Tenant Database Configure'),
                           tableName=_('Edit Tenant Database'), form=form,app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           editTitle=('Edit Tenant Database'))


# ---------------------------------------------------------------------------------------
# app manage code configure
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_code_configure', methods=['GET', 'POST'])
@login_required
def app_manage_code_configure():
    if session.get('validate_repo'):
        form = AddAppCodeForm(session['validate_repo'])
    else:
        form = AddAppCodeForm(None)
    if form.validate_on_submit():
        current_data = AppCode.query.filter(AppCode.app_id == session['current_selected_app_id']).first()
        current_data.repo = form.code_repo.data
        current_data.app_expand_id = AppExpand.query.filter(AppExpand.type == form.app_type.data).first().id
        current_data.db_config_path = form.db_config_path.data
        app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
        print(app_id)
        # app_id = 'fe01ce2a7fbac8fafaed7c982a04e229'

        current_data.remote_login_configure_path = form.remote_login_config_path.data
        current_data.remote_login_using_flag = form.remote_login_using_flag.data
        # current_data.remote_login_using_content = form.remote_login_using_content.data
        if hasattr(form.remote_login_using_content.data, 'filename'):
            filename1 = secure_filename(form.remote_login_using_content.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.remote_login_using_content.data.save(filePath1)
            current_data.remote_login_using_content = filePath1

        form.library_path.data = current_data.library_path
        form.filter_package_path.data = current_data.filter_package_path
        # form.filter_content.data = current_data.filter_content
        form.filter_config_path.data = current_data.filter_configure_path
        if hasattr(form.filter_content.data, 'filename'):
            filename1 = secure_filename(form.filter_content.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.filter_content.data.save(filePath1)
            current_data.filter_content = filePath1

        form.filter_import_flag.data = current_data.filter_import_flag
        # form.filter_import_content.data = current_data.filter_import_content
        form.filter_using_flag.data = current_data.filter_using_flag
        # form.filter_using_content.data = current_data.filter_using_content
        if hasattr(form.filter_import_content.data, 'filename'):
            filename1 = secure_filename(form.filter_import_content.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.filter_import_content.data.save(filePath1)
            current_data.filter_import_content = filePath1
        if hasattr(form.filter_using_content.data, 'filename'):
            filename1 = secure_filename(form.filter_using_content.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.filter_using_content.data.save(filePath1)
            current_data.filter_using_content = filePath1

        # form.call_starting_point.data = current_data.call_starting_point
        # form.third_party_packages.data = current_data.third_party_packages
        if hasattr(form.call_starting_point.data, 'filename'):
            filename1 = secure_filename(form.call_starting_point.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.call_starting_point.data.save(filePath1)
            current_data.call_starting_point = filePath1
        if hasattr(form.third_party_packages.data, 'filename'):
            filename1 = secure_filename(form.third_party_packages.data.filename)
            filePath1 = os.path.join(os.path.join(current_app.config['UPLOAD_FOLDERS']['app_manage_code_configure'],
                                                  app_id), filename1).replace('\\', '/')
            form.third_party_packages.data.save(filePath1)
            current_data.third_party_packages = filePath1

        db.session.commit()
        flash(_('Code configuration have been edited.'))
        return redirect(url_for('main.app_manage_code_configure'))
    elif request.method == 'GET':
        current_data = AppCode.query.filter(AppCode.app_id == session['current_selected_app_id']).first()
        current_extension_data = AppExpand.query.filter(AppExpand.id == current_data.app_expand_id).first()

        form.app_type.data = current_extension_data.type
        form.code_repo.data = current_data.repo
        form.tag_begin.data = current_extension_data.pattern_begin
        form.tag_end.data = current_extension_data.pattern_end
        form.db_config_path.data = current_data.db_config_path
        form.remote_login_config_path.data = current_data.remote_login_configure_path
        form.remote_login_using_flag.data = current_data.remote_login_using_flag
        # form.remote_login_using_content.data = current_data.remote_login_using_content
        form.remote_login_using_content.description = _('Selected File: ') + current_data.remote_login_using_content

        form.library_path.data = current_data.library_path
        form.filter_package_path.data = current_data.filter_package_path
        # form.filter_content.data = current_data.filter_content
        form.filter_content.description = _('Selected File: ') + current_data.filter_content
        form.filter_config_path.data = current_data.filter_configure_path

        form.filter_import_flag.data = current_data.filter_import_flag
        # form.filter_import_content.data = current_data.filter_import_content
        form.filter_import_content.description = _('Selected File: ') + current_data.filter_import_content
        form.filter_using_flag.data = current_data.filter_using_flag
        # form.filter_using_content.data = current_data.filter_using_content
        form.filter_using_content.description = _('Selected File: ') + current_data.filter_using_content

        # form.call_starting_point.data = current_data.call_starting_point
        # form.third_party_packages.data = current_data.third_party_packages
        form.call_starting_point.description = _('Selected File: ') + current_data.call_starting_point
        form.third_party_packages.description = _('Selected File: ') + current_data.third_party_packages

        session['validate_repo'] = form.code_repo.data
    return render_template('app_manage_code_configure.html', title=_('Edit Code Information'),
                           tableName=_('Edit Code Information'), form=form, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name())


# ---------------------------------------------------------------------------------------
# app manage mirror list
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_mirror_list')
@login_required
def app_manage_mirror_list():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Mirror Name'), _('Creator'), _('Created Time')]
    data = [App.query.order_by(db.asc(App.name)).first()]
    return render_template('app_manage_mirror_list.html', title=_('Mirror Manage'),
                           tableName=_('Mirror List'), AppAdmin=AppAdmin, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/app_manage_mirror_list_add', methods=['GET', 'POST'])
@login_required
def app_manage_mirror_list_add():
    logPath = 'logs/mirror_construct.log'
    if os.path.isfile(logPath):
        # os.remove(logPath)
        pass
    new_log_file = open(logPath, 'w', encoding='utf-8')
    new_log_file.write('')
    new_log_file.flush()
    new_log_file.close()

    app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
    current_code = AppCode.query.filter(AppCode.app_id == session['current_selected_app_id']).first()
    mirror_construction(current_app._get_current_object(), app_id, current_code)
    return jsonify({'code': '0', 'logPath': logPath, 'message': 'Operation done.'})


@bp.route('/app_manage_mirror_list_delete/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_mirror_list_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = TenantDb.query.filter(TenantDb.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Tenant'), _('Is System Extension'), _('Database'), _('IP'), _('Port')]
    data = TenantDb.query.filter(TenantDb.app_id == session['current_selected_app_id']).order_by(
        db.asc(TenantDb.username)).all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('app_manage_mirror_list.html', title=_('Tenant Database List'),
                           tableName=_('Tenant Database List'), Tenant=Tenant, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/app_manage_mirror_list_delete_select', methods=['GET', 'POST'])
@login_required
def app_manage_mirror_list_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.app_manage_mirror_list'))


@bp.route('/app_manage_mirror_list_edit/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_mirror_list_edit(id):
    if session.get('validate_alias_name'):
        form = EditTenantDatabaseForm(session['validate_alias_name'])
    else:
        form = EditTenantDatabaseForm(None)
    if form.validate_on_submit():
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        current_data.hostname = form.host_name.data
        current_data.driver = form.database_driver.data
        current_data.username = form.user_name.data
        current_data.database = form.database_name.data
        current_data.port = form.database_port.data
        current_data.aliasname = '_'.join([form.database_driver.data, form.database_name.data])
        current_data.type = 'system' if form.system_extension.data == 'System Extension' else 'origin'
        current_data.tenant_id = Tenant.query.filter(Tenant.name == form.tenant_name.data).first().id
        current_data.app_id = session['current_selected_app_id']
        if not form.user_password.data.strip() == '':
            current_data.password = generate_password_hash(form.user_password.data)
        db.session.commit()
        flash(_('Tenant Database have been edited.'))
        return redirect(url_for('main.app_manage_mirror_list'))
    elif request.method == 'GET':
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        form.app_name.data = session['current_selected_app_name']
        form.host_name.data = current_data.hostname
        form.database_port.data = current_data.port
        form.system_extension.data = 'System Extension' if current_data.type == 'system' else 'Not System Extension'
        form.database_driver.data = current_data.driver
        form.database_name.data = current_data.database
        form.user_name.data = current_data.username
        form.user_password.description = 'In edit mode, set null in this field means no modification for current password.'
        session['validate_alias_name'] = '_'.join([form.database_driver.data, form.database_name.data])
    return render_template('app_manage_mirror_list.html', title=_('Tenant Database Configure'),
                           tableName=_('Edit Tenant Database'), form=form,app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           editTitle=('Edit Tenant Database'))


@bp.route('/get_log', methods=['GET', 'POST'])
@login_required
def get_log():
    logStr = ''
    data = request.get_json()
    if os.path.isfile(data['file']):
        logStr = open(data['file']).read()[data['start']:]
        pos = data['start'] + len(logStr)
        hasMore = True
        if 'Operation done.' in logStr:
            hasMore = False
        return jsonify({'code': '0', 'log': logStr.replace('\n', '<br/>'), 'pos': pos, 'hasMore': hasMore})
    else:
        print('debug1', data['file'])
        print('debug1', os.path.isfile(data['file']))
        print('debug1', os.path.exists(data['file']))
        return jsonify({'code': '-1', 'message': 'Log file not exist.%s'%(data['file'])})


@bp.route('/remove_log', methods=['GET', 'POST'])
@login_required
def remove_log():
    data = request.get_json()
    if os.path.isfile(data['file']):
        # os.remove(data['file'])
        clear_file = open(data['file'], 'w')
        clear_file.write('')
        clear_file.flush()
        clear_file.close()
    return jsonify({'code': '0', 'message': 'remove log at %s' % (datetime.utcnow())})


# mirror construction
@async
def mirror_construction(app, app_id, current_code):
    with app.app_context() and app.request_context(EnvironBuilder('/','http://localhost/').get_environ()):
    # with app.app_context():
        remove_log()

        logger.info('Operation begin:\n')
        logger.info('1.------Reading function package, atomic function data of app------')

        #read app function json
        tag = 'package2function.json'
        filePath = os.path.join(os.path.join(
            current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id), tag)
        if os.path.isfile(filePath):
            json_dict = json.load(open(filePath, encoding='utf-8'))
            for a in json_dict:
                id = a['id']
                if 'file_path' in a['data'] and 'item_pattern' in a['data']:
                    file_path = a['data']['file_path']
                    item_pattern = a['data']['item_pattern']
                    # logger.info('id: %s\nfile_path: %s\nitem_pattern: %s', id, file_path, item_pattern)

            logger.info('2.------Pulling code from registry------')
            sourceSrcDir = 'F:/code/PPGo_ApiAdmin'
            dstSrcDir = 'F:/code/Tenant_PPGo_ApiAdmin'

            if os.path.exists(dstSrcDir):
                # print('rmtree')
                shutil.rmtree(dstSrcDir)
            # print('copytree')
            shutil.copytree(sourceSrcDir, dstSrcDir)

            logger.info('3.------insert tag template in code------')
            # 切换工作目录易引起线程安全问题
            # old_cwd = os.getcwd()
            # os.chdir(dstSrcDir)
            args = ''
            for a in json_dict:
                if 'file_path' in a['data'] and 'item_pattern' in a['data'] and\
                                a['data']['file_path'] is not '' and a['data']['item_pattern'] is not '':
                    # filePath = 'F:/test/main.html'
                    filePath = os.path.join(dstSrcDir, a['data']['file_path']).replace('\\', '/')
                    # pattern = 'x;/<dd>.*API监控.*<\/dd>/{p;q};/<dd>.*<\/dd>/{x;h;d;ta};/<dd>.*/{x;H;ta};{x;h;d};:a'
                    pattern = a['data']['item_pattern']
                    # tag_begin = '{if .role_APIguanli}'
                    tag_begin = '{{if .role_%s}}' % (a['id'])
                    tag_end = '{{end}}'
                    args += 'cat -n %s | sed -n "%s" | { eval $(awk \'NR==1{print "a="$1} END {print "b="$1}\'); ' \
                            'sed -e "$a i %s" -e "$b a %s" %s;} > F:/temp.txt\n cp F:/temp.txt %s\n' % \
                           (filePath, pattern, tag_begin, tag_end, filePath, filePath)

            shell_file = open('F:/test/temp.sh', 'w', encoding='utf-8')
            shell_file.write(args)
            shell_file.flush()
            shell_file.close()
            exec_path = "D:\Program Files\Git\git-bash.exe"
            # (status, output) = subprocess.getstatusoutput([exec_path, 'F:/test/temp.sh'])
            CREATE_NO_WINDOW = 0x08000000
            subprocess.call([exec_path, 'F:/test/temp.sh'], creationflags=CREATE_NO_WINDOW)
            # os.chdir(old_cwd)

            logger.info('4.------initialing tenant database connection------')
            pass

            logger.info('5.------extending filter code------')

            filter_package_path = os.path.join(dstSrcDir, current_code.filter_package_path).replace('\\', '/')
            filter_content = current_code.filter_content
            if not os.path.isdir(filter_package_path):
                os.makedirs(filter_package_path)
            old_filter_file = os.path.join(filter_package_path, os.path.basename(filter_content)).replace('\\', '/')
            if os.path.isfile(old_filter_file):
                os.remove(old_filter_file)
            shutil.copyfile(filter_content, os.path.join(filter_package_path, os.path.basename(filter_content).replace('\\', '/')))

            filter_config_path = os.path.join(dstSrcDir, current_code.filter_configure_path).replace('\\', '/')
            filter_import_flag = current_code.filter_import_flag
            filter_import_content = current_code.filter_import_content
            filter_using_flag = current_code.filter_using_flag
            filter_using_content = current_code.filter_using_content

            with open(filter_config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(filter_config_path, "w", encoding="utf-8") as f_w:
                for line in lines:
                    if filter_import_flag in line:
                        f_w.write(line)
                        pre = line[:line.index(filter_import_flag)]
                        wlines = open(filter_import_content, encoding="utf-8").readlines()
                        for l in wlines:
                            f_w.write(pre + l)
                        # f_w.write(open(filter_import_content, encoding="utf-8").read())
                    elif filter_using_flag in line:
                        f_w.write(line)
                        pre = line[:line.index(filter_using_flag)]
                        wlines = open(filter_using_content, encoding="utf-8").readlines()
                        for l in wlines:
                            f_w.write(pre + l)
                        # f_w.write(open(filter_using_content, encoding="utf-8").read())
                    else:
                        f_w.write(line)

            logger.info('6.------extending remote login code------')
            remote_login_config_path = os.path.join(dstSrcDir, current_code.remote_login_configure_path)
            remote_login_using_flag = current_code.remote_login_using_flag
            remote_login_using_content = current_code.remote_login_using_content
            with open(remote_login_config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 写的方式打开文件
            with open(remote_login_config_path, "w", encoding="utf-8") as f_w:
                for line in lines:
                    if remote_login_using_flag in line:
                        pre = line[:line.index(remote_login_using_flag)]
                        f_w.write(line)
                        wlines = open(remote_login_using_content, encoding="utf-8").readlines()
                        for l in wlines:
                            f_w.write(pre + l)
                    else:
                        f_w.write(line)
            # 补充库文件
            library_src_path = os.path.join(current_app.config['UPLOAD_FOLDERS']['library_path'],
                                            'go beego\\saas_support')
            library_dst_path = os.path.join(os.path.join(dstSrcDir, current_code.library_path), 'saas_support')
            # if os.path.exists(library_path):
            #     # print('rmtree')
            #     shutil.rmtree(library_path)
            # print('copytree')
            shutil.copytree(library_src_path, library_dst_path)

            logger.info('7.------packing mirror------')
            file_handler.setFormatter(blank_formatter)  # 改变格式
            # subprocess.call([exec_path, 'docker build -t testdocker:v1 %s'%(dstSrcDir)], creationflags=CREATE_NO_WINDOW)
            # state, output = subprocess.getstatusoutput('docker build -t testdocker:v1 %s'%(dstSrcDir))
            cmd = 'docker build -t reg.silvermaple.com/demo/demo:1.0.0 %s'%(dstSrcDir)

            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while p.poll() is None:
                line = p.stdout.readline()
                line = line.strip()
                if line:
                    logger.info(str(line, encoding = "utf-8"))
            if p.returncode == 0:
                logger.info('Mirror packed success.')
            else:
                logger.info('Mirror packed failed.')

            file_handler.setFormatter(formatter)  # 指定输出格式
            logger.info('8.------uploading mirror------')
            file_handler.setFormatter(blank_formatter)
            cmd = 'docker push reg.silvermaple.com/demo/demo:1.0.0'
            # state, output = subprocess.getstatusoutput(cmd)
            # logger.info(output)
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while p.poll() is None:
                line = p.stdout.readline()
                line = line.strip()
                if line:
                    logger.info(str(line, encoding = "utf-8"))
            if p.returncode == 0:
                logger.info('Mirror uploaded success.')
            else:
                logger.info('Mirror uploaded failed.')
            file_handler.setFormatter(formatter)  # 指定输出格式
            logger.info('Operation done.')
        else:
            logger.info('File package2function.json not exist.\nOperation done.')
            return jsonify({'code': '-1', 'message': 'File package2function.json not exist.'})

        return jsonify({'code': '0', 'message': 'Success'})


# ---------------------------------------------------------------------------------------
# app manage service deploy
# ---------------------------------------------------------------------------------------
@bp.route('/app_manage_service_deploy')
@login_required
def app_manage_service_deploy():
    isCheck = True
    isEdit = True
    isDelete = False
    session['is_delete'] = 'false'
    tHead = [_('ID'), _('Mirror'), _('Instance Number'), _('State'), _('Action')]
    action_list = [_('Publish'), _('Adjust'), _('Restart'), _('Stop'), _('Destroy')]
    data = [App.query.order_by(db.asc(App.name)).first()]
    return render_template('app_manage_service_deploy.html', title=_('Service Deploy'),
                           tableName=_('Service Container List'), action_list=action_list, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/app_manage_service_deploy_add', methods=['GET', 'POST'])
@login_required
def app_manage_service_deploy_add():
    form = True
    if request.method == 'POST':
    # if form.validate_on_submit():
    #     current_tenant_id = Tenant.query.filter(Tenant.name == form.tenant_name.data).first().id
    #     current_type = 'system' if form.system_extension.data == 'System Extension' else 'origin'
    #     db.session.add(TenantDb(id=None, hostname=form.host_name.data, driver=form.database_driver.data,
    #                             username=form.user_name.data,
    #                             password=generate_password_hash(form.user_password.data),
    #                             database=form.database_name.data, port=form.database_port.data,
    #                             aliasname='_'.join([form.database_driver.data, form.database_name.data]),
    #                             type=current_type, tenant_id=current_tenant_id, app_id=session['current_selected_app_id']))
    #     db.session.commit()
        flash(_('New tenant database have been added.'))
        return redirect(url_for('main.app_manage_service_deploy'))
    elif request.method == 'GET':
        # form.app_name.data = session['current_selected_app_name']
        # form.host_name.data = 'localhost'
        # form.database_port.data = '3306'
        # form.database_driver.data = 'mysql'
        # form.user_name.data = 'root'
        pass
    return render_template('app_manage_service_deploy.html', title=_('Service Deploy'),
                           tableName=_('Add New Container'), form=form, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           addTitle=('Add New Container'))


@bp.route('/app_manage_service_deploy_delete/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_service_deploy_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = TenantDb.query.filter(TenantDb.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Tenant'), _('Is System Extension'), _('Database'), _('IP'), _('Port')]
    data = TenantDb.query.filter(TenantDb.app_id == session['current_selected_app_id']).order_by(
        db.asc(TenantDb.username)).all()
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('app_manage_service_deploy.html', title=_('Tenant Database List'),
                           tableName=_('Tenant Database List'), Tenant=Tenant, app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)


@bp.route('/app_manage_service_deploy_delete_select', methods=['GET', 'POST'])
@login_required
def app_manage_service_deploy_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.app_manage_service_deploy'))


@bp.route('/app_manage_service_deploy_edit/<id>', methods=['GET', 'POST'])
@login_required
def app_manage_service_deploy_edit(id):
    if session.get('validate_alias_name'):
        form = EditTenantDatabaseForm(session['validate_alias_name'])
    else:
        form = EditTenantDatabaseForm(None)
    if form.validate_on_submit():
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        current_data.hostname = form.host_name.data
        current_data.driver = form.database_driver.data
        current_data.username = form.user_name.data
        current_data.database = form.database_name.data
        current_data.port = form.database_port.data
        current_data.aliasname = '_'.join([form.database_driver.data, form.database_name.data])
        current_data.type = 'system' if form.system_extension.data == 'System Extension' else 'origin'
        current_data.tenant_id = Tenant.query.filter(Tenant.name == form.tenant_name.data).first().id
        current_data.app_id = session['current_selected_app_id']
        if not form.user_password.data.strip() == '':
            current_data.password = generate_password_hash(form.user_password.data)
        db.session.commit()
        flash(_('Tenant Database have been edited.'))
        return redirect(url_for('main.app_manage_service_deploy'))
    elif request.method == 'GET':
        current_data = TenantDb.query.filter(TenantDb.id == id).first()
        form.app_name.data = session['current_selected_app_name']
        form.host_name.data = current_data.hostname
        form.database_port.data = current_data.port
        form.system_extension.data = 'System Extension' if current_data.type == 'system' else 'Not System Extension'
        form.database_driver.data = current_data.driver
        form.database_name.data = current_data.database
        form.user_name.data = current_data.username
        form.user_password.description = 'In edit mode, set null in this field means no modification for current password.'
        session['validate_alias_name'] = '_'.join([form.database_driver.data, form.database_name.data])
    return render_template('app_manage_service_deploy.html', title=_('Tenant Database Configure'),
                           tableName=_('Edit Tenant Database'), form=form,app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           editTitle=('Edit Tenant Database'))


# ---------------------------------------------------------------------------------------
# tenant service customize function
# ---------------------------------------------------------------------------------------
@bp.route('/tenant_service_customize_function')
@login_required
def tenant_service_customize_function():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.order_by(db.asc(App.name)).all()
    # flash(_('Batch delete operation are not allowed now.'))
    return render_template('tenant_service_customize_function.html', title=_('Customized Function'),
                           tableName=_('Function Root'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/tenant_service_customize_function_edit')
@login_required
def tenant_service_customize_function_edit():
    form = True
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    data = App.query.order_by(db.asc(App.name)).all()
    return render_template('tenant_service_customize_function.html', title=_('Customized Function'),
                           editTitle=_('Customize'),
                           tableName=_('Function Root'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, form=form,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/tenant_service_customize_function_save', methods=['GET', 'POST'])
@login_required
def tenant_service_customize_function_save():
    data = request.get_json()
    tenant_id = Tenant.query.filter(Tenant.id == session['current_tenant_id']).first().tenantid
    filePath = os.path.join(
        current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function'], tenant_id)

    if not os.path.isdir(filePath):
        os.makedirs(filePath)

    tag = data['tag']
    new_json = json.loads(data['json'])
    # print(new_json)
    # print(tag)
    if tag in ['version2function.json']:
        try:
            new_file = open(os.path.join(filePath, tag), 'w')
            # new_file.write(json.dumps(new_json))
            # json.dump(new_json, new_file, ensure_ascii=False, indent=4)
            json.dump(new_json, new_file, indent=4)
            new_file.close()
            flash(_('File save for %(tag)s success.', tag=tag))
        except Exception as e:
            print(e)
            flash(_('File save for %(tag)s failed.', tag=tag))
    return jsonify({'result': 'success'})


@bp.route('/get_tenant_customize_file_path/<tag>', methods=['GET', 'POST'])
@login_required
def get_tenant_customize_file_path(tag):
    tenant_id = Tenant.query.filter(Tenant.id == session['current_tenant_id']).first().tenantid
    if tag == 'version2function.json':
        filePath = os.path.join(os.path.join(
            current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function'], tenant_id), tag)
        if os.path.isfile(filePath):
            filePath = os.path.join(os.path.join(
                current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function_html'], tenant_id), tag)
            return jsonify({'result': 'success', 'filePath': filePath})
        # filePath1 = os.path.join(
        #     current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function'], tenant_id)
        # if not os.path.isdir(filePath1):
        #     os.makedirs(filePath1)
        #     app_id = App.query.filter(App.id == session['current_selected_app_id']).first().appid
        #     app_file = os.path.join(os.path.join(
        #         current_app.config['UPLOAD_FOLDERS']['app_manage_function_configure'], app_id), 'version2package.json')
        #     shutil.copyfile(app_file, filePath)
        #     filePath = os.path.join(os.path.join(
        #         current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function_html'], tenant_id), tag)
        #     return jsonify({'result': 'success', 'filePath': filePath})
    # flash(_('No customize function now!'))
    return jsonify({'result': 'fail', 'filePath': False})


# ---------------------------------------------------------------------------------------
# tenant service customize function
# ---------------------------------------------------------------------------------------
@bp.route('/tenant_service_role_setting')
@login_required
def tenant_service_role_setting():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Role Name'), _('Creator'), _('App Name')]
    data = SaasRole.query.order_by(db.asc(SaasRole.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    # flash(_('Batch delete operation are not allowed now.'))
    return render_template('tenant_service_role_setting.html', title=_('Role List'),
                           tableName=_('Role List'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/tenant_service_role_setting_allocate/<id>', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_allocate(id):
    form = True
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    session['current_role_id'] = id
    tHead = [_('Role Name'), _('Creator'), _('App Name')]
    data = SaasRole.query.order_by(db.asc(SaasRole.name)).all()
    role_name = SaasRole.query.filter(SaasRole.id==id).first().name
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    # flash(_('Batch delete operation are not allowed now.'))
    return render_template('tenant_service_role_setting.html', title=_('Role List'),
                           tableName=_('Allocate Function'), app_name_list=get_app_name_list(), form=form, role_id=id,
                           current_selected_app_name=get_current_selected_app_name(), role_name=role_name,
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data, role_tag_prefix='role_')


@bp.route('/tenant_service_role_setting_save', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_save():
    data = request.get_json()
    role_id = session['current_role_id']
    tenant_id = Tenant.query.filter(Tenant.id == session['current_tenant_id']).first().tenantid
    filePath = os.path.join(os.path.join(
        current_app.config['UPLOAD_FOLDERS']['tenant_service_role_setting'], tenant_id), role_id)

    if not os.path.isdir(filePath):
        os.makedirs(filePath)

    tag = data['tag']
    new_json = json.loads(data['json'])
    print(new_json)
    print(tag)
    if tag in ['version2function.json']:
        try:
            new_file = open(os.path.join(filePath, tag), 'w')
            # new_file.write(json.dumps(new_json))
            # json.dump(new_json, new_file, ensure_ascii=False, indent=4)
            json.dump(new_json, new_file, indent=4)
            new_file.close()
            flash(_('File save for %(tag)s success.', tag=tag))
        except Exception as e:
            print(e)
            flash(_('File save for %(tag)s failed.', tag=tag))
    return jsonify({'result': 'success'})


@bp.route('/get_role_customize_file_path/<tag>', methods=['GET', 'POST'])
@login_required
def get_role_customize_file_path(tag):
    tenant_id = Tenant.query.filter(Tenant.id == session['current_tenant_id']).first().tenantid
    role_id = session['current_role_id']
    if tag == 'version2function.json':
        filePath = os.path.join(os.path.join(os.path.join(
            current_app.config['UPLOAD_FOLDERS']['tenant_service_role_setting'], tenant_id), role_id), tag)
        if os.path.isfile(filePath):
            filePath = os.path.join(os.path.join(os.path.join(
                current_app.config['UPLOAD_FOLDERS']['tenant_service_role_setting_html'], tenant_id), role_id), tag)
            return jsonify({'result': 'success', 'filePath': filePath})
    return jsonify({'result': 'fail', 'filePath': False})


@bp.route('/tenant_service_role_setting_add', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_add():
    form = AddRoleForm(None)
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    if form.validate_on_submit():
        db.session.add(SaasRole(id=None, name=form.role_name.data, funcdata_mod_time=datetime.now().__str__()))
        db.session.commit()
        flash(_('New role have been added.'))
        return redirect(url_for('main.tenant_service_role_setting'))
    elif request.method == 'GET':
        form.creator.data = current_tenant_name
        form.app_name.data = get_current_selected_app_name()
        pass

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('App Name'), _('App ID'), _('Creator')]
    # flash(_('Batch delete operation are not allowed now.'))
    return render_template('tenant_service_role_setting.html', title=_('Role List'), form=form,
                           tableName=_('Add Role'), app_name_list=get_app_name_list(), addTitle=_('Add Role'),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead)


@bp.route('/tenant_service_role_setting_delete/<id>', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = SaasRole.query.filter(SaasRole.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Role Name'), _('Creator'), _('App Name')]
    data = SaasRole.query.order_by(db.asc(SaasRole.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('tenant_service_role_setting.html', title=_('Role List'),
                           tableName=_('Role List'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)



@bp.route('/tenant_service_role_setting_delete_select', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.tenant_service_role_setting'))


@bp.route('/tenant_service_role_setting_edit/<id>', methods=['GET', 'POST'])
@login_required
def tenant_service_role_setting_edit(id):
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    if session.get('validate_role_name'):
        form = AddRoleForm(session['validate_role_name'])
    else:
        form = AddRoleForm(None)
    if form.validate_on_submit():
        current_data = SaasRole.query.filter(SaasRole.id == id).first()
        current_data.name = form.role_name.data
        db.session.commit()
        flash(_('Role have been edited.'))
        return redirect(url_for('main.tenant_service_role_setting'))
    elif request.method == 'GET':
        current_data = SaasRole.query.filter(SaasRole.id == id).first()
        form.role_name.data = current_data.name
        form.creator.data = current_tenant_name
        form.app_name.data = get_current_selected_app_name()
        session['validate_role_name'] = form.role_name.data

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('Role Name'), _('Creator'), _('App Name')]
    data = SaasRole.query.order_by(db.asc(SaasRole.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    return render_template('tenant_service_role_setting.html', title=_('Role List'), form=form,
                           tableName=_('Edit Role'), app_name_list=get_app_name_list(), editTitle=_('Edit Role'),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data)


# ---------------------------------------------------------------------------------------
# tenant service customize function
# ---------------------------------------------------------------------------------------
@bp.route('/tenant_service_user_setting')
@login_required
def tenant_service_user_setting():
    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('User Name'), _('Belonged Role'), _('Creator'), _('App Name')]
    data = SaasUser.query.order_by(db.asc(SaasUser.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    return render_template('tenant_service_user_setting.html', title=_('User List'),
                           tableName=_('User List'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           current_tenant_name=current_tenant_name,
                           isCheck=isCheck, isEdit=isEdit, SaasRole=SaasRole,
                           isDelete=isDelete, tHead=tHead, data=data)


@bp.route('/tenant_service_user_setting_add', methods=['GET', 'POST'])
@login_required
def tenant_service_user_setting_add():
    form = AddUserForm(None)
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    if form.validate_on_submit():
        role_id = SaasRole.query.filter(SaasRole.name == form.role_list.data).first().id
        db.session.add(SaasUser(id=None, name=form.user_name.data,
                                password=generate_password_hash(form.user_password.data),
                                role_id=role_id))
        db.session.commit()
        flash(_('New user have been added.'))
        return redirect(url_for('main.tenant_service_user_setting'))
    elif request.method == 'GET':
        form.creator.data = current_tenant_name
        form.app_name.data = get_current_selected_app_name()
        pass

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('User Name'), _('Belonged Role'), _('Creator'), _('App Name')]
    # flash(_('Batch delete operation are not allowed now.'))
    return render_template('tenant_service_user_setting.html', title=_('User List'), form=form,
                           tableName=_('Add User'), app_name_list=get_app_name_list(), addTitle=_('Add User'),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit,
                           isDelete=isDelete, tHead=tHead)


@bp.route('/tenant_service_user_setting_delete/<id>', methods=['GET', 'POST'])
@login_required
def tenant_service_user_setting_delete(id):
    if request.method == 'GET':
        session['current_delete_id'] = id
    else:
        data = request.get_json()
        name = data.get('name')
        if name == 'execute':
            current_data = SaasUser.query.filter(SaasUser.id == session['current_delete_id']).first()
            db.session.delete(current_data)
            db.session.commit()
            flash(_('Record have been deleted.'))
            return jsonify({'result': 'success'})

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('User Name'), _('Belonged Role'), _('Creator'), _('App Name')]
    data = SaasUser.query.order_by(db.asc(SaasUser.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    confirmTitle = 'Confirm your choice:'
    confirmMessage = 'Do you want to delete this record?'
    return render_template('tenant_service_user_setting.html', title=_('User List'),
                           tableName=_('User List'), app_name_list=get_app_name_list(),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data, SaasRole=SaasRole,
                           confirmTitle=confirmTitle, confirmMessage=confirmMessage)




@bp.route('/tenant_service_user_setting_delete_select', methods=['GET', 'POST'])
@login_required
def tenant_service_user_setting_delete_select():
        flash(_('Batch delete operation are not allowed now.'))
        return redirect(url_for('main.tenant_service_user_setting'))


@bp.route('/tenant_service_user_setting_edit/<id>', methods=['GET', 'POST'])
@login_required
def tenant_service_user_setting_edit(id):
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    if session.get('validate_user_name'):
        form = AddUserForm(session['validate_user_name'])
    else:
        form = AddUserForm(None)
    if form.validate_on_submit():
        current_data = SaasUser.query.filter(SaasUser.id == id).first()
        current_data.name = form.user_name.data
        if not form.user_password.data.strip() == '':
            current_data.password = generate_password_hash(form.user_password.data)
        current_data.role_id = SaasRole.query.filter(SaasRole.name==form.role_list.data).first().id
        db.session.commit()
        flash(_('Role have been edited.'))
        return redirect(url_for('main.tenant_service_user_setting'))
    elif request.method == 'GET':
        current_data = SaasUser.query.filter(SaasUser.id == id).first()
        form.user_name.data = current_data.name
        form.role_list.data = SaasRole.query.filter(SaasRole.id==current_data.role_id).first().name
        form.creator.data = current_tenant_name
        form.app_name.data = get_current_selected_app_name()
        session['validate_user_name'] = form.user_name.data

    isCheck = True
    isEdit = True
    isDelete = True
    session['is_delete'] = 'false'
    tHead = [_('User Name'), _('Belonged Role'), _('Creator'), _('App Name')]
    data = SaasUser.query.order_by(db.asc(SaasUser.name)).all()
    current_tenant_id = session['current_tenant_id']
    current_tenant_name = Tenant.query.filter(Tenant.id == current_tenant_id).first().name
    return render_template('tenant_service_role_setting.html', title=_('User List'), form=form,
                           tableName=_('User List'), app_name_list=get_app_name_list(), editTitle=_('Edit User'),
                           current_selected_app_name=get_current_selected_app_name(),
                           isCheck=isCheck, isEdit=isEdit, current_tenant_name=current_tenant_name,
                           isDelete=isDelete, tHead=tHead, data=data)


# ---------------------------------------------------------------------------------------
# remote api service
# ---------------------------------------------------------------------------------------
HTTPMETHOD = {
    'GET':     "GET",
    'POST':    "POST",
    'PUT':     "PUT",
    'DELETE':  "DELETE",
    'PATCH':   "PATCH",
    'OPTIONS': "OPTIONS",
    'HEAD':    "HEAD",
    'TRACE':   "TRACE",
    'CONNECT': "CONNECT",
}

ErrMsgs = {
    'FAILED':       "Failed;",
    'NOTFOUND':     "Not found;",
    'SUCCESS':      "Success;",
    'UNEXPECTED':   "Something unexpected happened;",
    'UNAUTHORIZED': "You are not authorized to do that;",
}

class ResponseBaseStruct():

    Success = True
    Errmsg = ErrMsgs['SUCCESS']

class ResponseStruct(ResponseBaseStruct):
    Data = {}
    HasMore = False
    Next = ''

def obj2json(obj):
    return {
        "Success": obj.Success,
        "Errmsg": obj.Errmsg,
        "Data": obj.Data,
        "HasMore": obj.HasMore,
        "Next": obj.Next
    }


@bp.route('/funcData', methods=['GET', 'POST'])
def getFuncData():
    # print(appID, tenantID, userName, accessToken)

    form = request.form
    appID = form['appID']
    tenantID = form['tenantID']
    data_json = None
    dataFile = os.path.join(os.path.join(os.path.join(
        current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function'],
        appID), tenantID), 'version2function.json')
    if os.path.isfile(dataFile):
        data_json = json.load(open(dataFile, 'r', encoding='utf-8'))
    rs = ResponseStruct()
    rs.Success = True
    rs.Errmsg = ErrMsgs['SUCCESS']
    rs.Data = {}
    rs.Data['ModTime'] = str(time.time())
    rs.Data['Info'] = []
    for v in data_json:
        print(v)
        rs.Data['Info'].append({'data': {}, 'id': 'role_' + v['id']})
    print(rs.Data)
    response = current_app.make_response((json.dumps(rs, default=obj2json), 200))
    # response = current_app.make_response((data_json, '200', 'application/json'))
    return response


@bp.route('/funcDataCheck', methods=['GET', 'POST'])
def funcDataCheck():
    form = request.form
    appID = form['appID']
    tenantID = form['tenantID']
    data_json = None
    dataFile = os.path.join(os.path.join(os.path.join(
        current_app.config['UPLOAD_FOLDERS']['tenant_service_customize_function'],
        appID), tenantID), 'version2function.json')

    if os.path.isfile(dataFile):
        data_json = json.load(open(dataFile, 'r', encoding='utf-8'))
    print(data_json)
    response = current_app.make_response("success", 200)
    return response