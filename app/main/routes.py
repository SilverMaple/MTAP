# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 14:53:17
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : routes.py

import hashlib
import json
import os
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app, session
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from flask_uploads import UploadSet
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, PostForm, SearchForm, AddAppForm, AddAppExtensionForm, EditAppExtensionForm, \
    AddAppAdminForm, AddTenantForm
from app.models import User, Post, App, AppAdmin, AppExpand, AdminToApp, Tenant
from app.translate import translate
from app.main import bp
from app.email import follower_notification
from app.auth import LoginType, current_login_type
from app import auth
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash


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
        return render_template('index_app_manage.html', title=_('Web App Manage'))
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
        print(form.library_file.data == None)
        print(form.library_file.data)
        form.library_file.description = _('Selected File: ') + os.path.basename(current_data.library_path)
        form.library_file_depend.description = _('Selected File: ') + os.path.basename(current_data.library_depend_path)

        # db.session.commit()
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