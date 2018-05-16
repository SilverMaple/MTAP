# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 14:52:41
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : forms.py

from flask import request, session
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SubmitField, TextAreaField, FileField, BooleanField, PasswordField, IntegerField, \
    SelectField, Label, Field
from wtforms.validators import ValidationError, DataRequired, Length
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from flask_babel import _, lazy_gettext as _l
from app.models import User, App, AppExpand, AppAdmin, Tenant, TenantDb, SaasRole, SaasUser


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))


class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)


class AddAppForm(FlaskForm):
    app_name = StringField(_l('App Name'), validators=[DataRequired()], render_kw={"placeholder": _('App Name')})
    app_ID = StringField(_l('App ID'), validators=[Length(min=0, max=140)],
                         render_kw={"placeholder": _('App ID'), "readonly": "readonly"})
    creator_name = StringField(_l('Creator'), validators=[Length(min=0, max=140)],
                             render_kw={"placeholder": _('Creator'), "readonly": "readonly"})
    # recaptcha = RecaptchaField('recaptcha here')
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

    def __init__(self, original_app_name, *args, **kwargs):
        super(AddAppForm, self).__init__(*args, **kwargs)
        self.original_app_name = original_app_name

    def validate_app_name(self, app_name):
        if app_name.data != self.original_app_name:
            app_entity = App.query.filter_by(name=self.app_name.data).first()
            if app_entity is not None:
                raise ValidationError(_('Please use a different app name.'))


class AddAppExtensionForm(FlaskForm):
    app_type = StringField(_l('App Type'), validators=[DataRequired()], render_kw={"placeholder": _('App Type')})
    tag_begin = StringField(_l('Tag Template(Begin)'), validators=[DataRequired()],
                            render_kw={"placeholder": _('Tip: role tag begins with $(role_tag)')})
    tag_end = StringField(_l('Tag Template(End)'), validators=[DataRequired()])
    library_file = FileField(_l('Library File'), validators=[DataRequired()])
    is_decompress = BooleanField(default=False)
    library_file_depend = FileField(_l('Library File Depend'), description="test hrere")
    library_file_description = TextAreaField(_l('Library File Description'))
    db_info_file_path = StringField(_l('Tenant DB Info File Path'), validators=[DataRequired(), Length(min=0, max=140)],
                             render_kw={"placeholder": _('Tip: initial tenant database info.')})
    # recaptcha = RecaptchaField('recaptcha here')
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

    def __init__(self, original_app_type, *args, **kwargs):
        super(AddAppExtensionForm, self).__init__(*args, **kwargs)
        self.original_app_type = original_app_type

    def validate_app_type(self, app_type):
        if app_type.data != self.original_app_type:
            app_type_entity = AppExpand.query.filter_by(type=self.app_type.data).first()
            if app_type_entity is not None:
                raise ValidationError(_('Please use a different app type name.'))


class EditAppExtensionForm(FlaskForm):
    app_type = StringField(_l('App Type'), validators=[DataRequired()], render_kw={"placeholder": _('App Type')})
    tag_begin = StringField(_l('Tag Template(Begin)'), validators=[DataRequired()],
                            render_kw={"placeholder": _('Tip: role tag begins with $(role_tag)')})
    tag_end = StringField(_l('Tag Template(End)'), validators=[DataRequired()])
    library_file = FileField(_l('Library File'))
    is_decompress = BooleanField(default=False)
    library_file_depend = FileField(_l('Library File Depend'), description="test hrere")
    library_file_description = TextAreaField(_l('Library File Description'))
    db_info_file_path = StringField(_l('Tenant DB Info File Path'), validators=[DataRequired(), Length(min=0, max=140)],
                             render_kw={"placeholder": _('Tip: initial tenant database info.')})
    # recaptcha = RecaptchaField('recaptcha here')
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

    def __init__(self, original_app_type, *args, **kwargs):
        super(EditAppExtensionForm, self).__init__(*args, **kwargs)
        self.original_app_type = original_app_type

    def validate_app_type(self, app_type):
        print(app_type.data, self.original_app_type)
        if app_type.data != self.original_app_type:
            app_type_entity = AppExpand.query.filter_by(type=self.app_type.data).first()
            if app_type_entity is not None:
                raise ValidationError(_('Please use a different app type name.'))

class AddAppAdminForm(FlaskForm):
    def __init__(self, original_app_admin_name, *args, **kwargs):
        super(AddAppAdminForm, self).__init__(*args, **kwargs)
        self.original_app_admin_name = original_app_admin_name

    def validate_app_admin_name(self, app_admin_name):
        if app_admin_name.data != self.original_app_admin_name:
            app_admin_entity = AppAdmin.query.filter_by(name=self.app_admin_name.data).first()
            if app_admin_entity is not None:
                raise ValidationError(_('Please use a different app admin name.'))

    def query_factory(self=None):
        return [r.name for r in App.query.all()]

    def get_pk(obj):
        return obj

    app_admin_name = StringField(_l('Admin Name'), validators=[DataRequired()], render_kw={"placeholder": _('Admin Name')})
    app_admin_password = PasswordField(_l('Admin Password'),
                                       description='In edit mode, set null in this field means no modification for current password.',
                                       render_kw={"placeholder": _('Admin Password')})
    # app_list = QuerySelectField(label=_l('App'), validators=[DataRequired()], query_factory=query_factory,
    #                             get_pk=get_pk, default='Please choose')
    app_list = QuerySelectMultipleField(label=_l('App'), query_factory=query_factory,
                                get_pk=get_pk, description=_('Please choose'))
    # recaptcha = RecaptchaField('recaptcha here')
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class AddTenantForm(FlaskForm):
    def __init__(self, original_app_tenant_name, *args, **kwargs):
        super(AddTenantForm, self).__init__(*args, **kwargs)
        self.original_app_tenant_name = original_app_tenant_name

    def validate_app_tenant_name(self, app_tenant_name):
        if app_tenant_name.data != self.original_app_tenant_name:
            app_tenant_entity = Tenant.query.filter_by(name=self.app_tenant_name.data).first()
            if app_tenant_entity is not None:
                raise ValidationError(_('Please use a different app tenant name.'))

    def query_factory(self=None):
        return [r.name for r in App.query.all()]

    def get_pk(obj):
        return obj

    tenant_name = StringField(_l('Tenant Name'), validators=[DataRequired()], render_kw={"placeholder": _('Tenant Name')})
    tenant_password = PasswordField(_l('Tenant Password'),
                                       description='In edit mode, set null in this field means no modification for current password.',
                                       render_kw={"placeholder": _('Tenant Password')})
    app_list = QuerySelectField(label=_l('App'), validators=[DataRequired()], query_factory=query_factory,
                                get_pk=get_pk, default='Please choose')
    tenant_id = StringField(_l('Tenant ID'), render_kw={"placeholder": _('Tenant ID'), "readonly": "readonly"})
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class AddTenantDatabaseForm(FlaskForm):
    def __init__(self, original_alias_name, *args, **kwargs):
        super(AddTenantDatabaseForm, self).__init__(*args, **kwargs)
        self.original_alias_name = original_alias_name

    def validate_database_name(self, database_name):
        if not self.validate_alias_name():
            raise ValidationError(_('Please use a different database name or different driver.'))

    # need to call positively
    def validate_alias_name(self):
        alias_name = '_'.join([self.database_driver.data, self.database_name.data])
        if alias_name != self.original_alias_name:
            db_entity = TenantDb.query.filter_by(aliasname=alias_name).first()
            if db_entity is not None:
                return False
                # raise ValidationError(_('Please use a different app name.'))
        return True

    def query_factory(self=None):
        return [r.name for r in Tenant.query.all()
                if TenantDb.query.filter(TenantDb.tenant_id == r.id,
                                         TenantDb.app_id == session['current_selected_app_id'])]

    def get_pk(obj):
        return obj

    app_name = StringField(_l('App Name'), validators=[DataRequired()],
                           render_kw={"placeholder": _('App Name'), "readonly": "readonly"})
    tenant_name = QuerySelectField(label=_l('Tenant Name'), validators=[DataRequired()], query_factory=query_factory,
                                   get_pk=get_pk, default='Please choose')
    host_name = StringField(_l('Host Name'), validators=[DataRequired()],
                            render_kw={"placeholder": _('Tenant Name')})
    database_port = IntegerField(_l('Database Port'), validators=[DataRequired()])
    system_extension = SelectField(label=_l('Is System Extension'), validators=[DataRequired()], default='Please choose',
                                   choices=[('System Extension', _('System Extension')),
                                            ('Not System Extension', _('Not System Extension'))])
    database_driver = StringField(_l('Database Driver'), validators=[DataRequired()],
                                  render_kw={"placeholder": _('Database Driver')})
    database_name = StringField(_l('Database Name'), validators=[DataRequired()],
                                 render_kw={"placeholder": _('Database Name')})
    user_name = StringField(_l('User Name'), validators=[DataRequired()], render_kw={"placeholder": _('User Name')})
    user_password=PasswordField(_l('Password'), validators=[DataRequired()], render_kw={"placeholder": _('Password')})
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class EditTenantDatabaseForm(FlaskForm):
    def __init__(self, original_alias_name, *args, **kwargs):
        super(EditTenantDatabaseForm, self).__init__(*args, **kwargs)
        self.original_alias_name = original_alias_name

    def validate_database_name(self, database_name):
        if not self.validate_alias_name():
            raise ValidationError(_('Please use a different database name or different driver.'))

    # need to call positively
    def validate_alias_name(self):
        alias_name = '_'.join([self.database_driver.data, self.database_name.data])
        if alias_name != self.original_alias_name:
            db_entity = TenantDb.query.filter_by(aliasname=alias_name).first()
            if db_entity is not None:
                return False
                # raise ValidationError(_('Please use a different app name.'))
        return True

    def query_factory(self=None):
        return [r.name for r in Tenant.query.all()
                if TenantDb.query.filter(TenantDb.tenant_id == r.id,
                                         TenantDb.app_id == session['current_selected_app_id'])]

    def get_pk(obj):
        return obj

    app_name = StringField(_l('App Name'), validators=[DataRequired()],
                           render_kw={"placeholder": _('App Name'), "readonly": "readonly"})
    tenant_name = QuerySelectField(label=_l('Tenant Name'), validators=[DataRequired()], query_factory=query_factory,
                                   get_pk=get_pk, default='Please choose')
    host_name = StringField(_l('Host Name'), validators=[DataRequired()],
                            render_kw={"placeholder": _('Tenant Name')})
    database_port = IntegerField(_l('Database Port'), validators=[DataRequired()])
    system_extension = SelectField(label=_l('Is System Extension'), validators=[DataRequired()], default='Please choose',
                                   choices=[('System Extension', _('System Extension')),
                                            ('Not System Extension', _('Not System Extension'))])
    database_driver = StringField(_l('Database Driver'), validators=[DataRequired()],
                                  render_kw={"placeholder": _('Database Driver')})
    database_name = StringField(_l('Database Name'), validators=[DataRequired()],
                                 render_kw={"placeholder": _('Database Name')})
    user_name = StringField(_l('User Name'), validators=[DataRequired()], render_kw={"placeholder": _('User Name')})
    user_password=PasswordField(_l('Password'), render_kw={"placeholder": _('Password')})
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class AddAppCodeForm(FlaskForm):
    def __init__(self, original_alias_name, *args, **kwargs):
        super(AddAppCodeForm, self).__init__(*args, **kwargs)
        self.original_alias_name = original_alias_name

    def validate_database_name(self, database_name):
        if not self.validate_alias_name():
            raise ValidationError(_('Please use a different database name or different driver.'))

    # need to call positively
    def validate_alias_name(self):
        alias_name = '_'.join([self.database_driver.data, self.database_name.data])
        if alias_name != self.original_alias_name:
            db_entity = TenantDb.query.filter_by(aliasname=alias_name).first()
            if db_entity is not None:
                return False
                # raise ValidationError(_('Please use a different app name.'))
        return True

    def query_factory(self=None):
        return [r.type for r in AppExpand.query.all()]

    def get_pk(obj):
        return obj

    label_name = Label(_('App Type'), text=_('App'))
    app_type = QuerySelectField(label=_l('App Type'), validators=[DataRequired()], query_factory=query_factory,
                                   get_pk=get_pk, default=True)
    label_tag = Label(_('App Type'), text=_('App'))
    code_repo = StringField(_l('Code Repo'), validators=[DataRequired()], render_kw={"placeholder": _('Code Repo')})
    tag_begin = StringField(_l('Tag Template(Begin)'), validators=[DataRequired()],
                            render_kw={"placeholder": _('Tip: role tag begins with $(role_tag)'), 'readonly':'readonly'})
    tag_end = StringField(_l('Tag Template(End)'), validators=[DataRequired()],
                          render_kw={'readonly': 'readonly'})
    db_config_path = StringField(_l('Database Config Path'), validators=[DataRequired()],
                            description= _('Tip: Runtime relative path'))
    remote_login_config_path = StringField(_l('Remote Login Config Path'), validators=[DataRequired()])
    remote_login_using_flag = StringField(_l('Using Flag'), validators=[DataRequired()])
    remote_login_using_content = FileField(_l('Using Content'))

    library_path = StringField(_l('Library Path'), validators=[DataRequired()])
    filter_package_path = StringField(_l('Filter Package Path'), validators=[DataRequired()])
    filter_content = FileField(_l('Filter Content'), validators=[DataRequired()])
    filter_config_path = StringField(_l('Filter Config Path'), validators=[DataRequired()])

    filter_import_flag = StringField(_l('Import Flag'))
    filter_import_content = FileField(_l('Import Content'))
    filter_using_flag = StringField(_l('Using Flag'), validators=[DataRequired()])
    filter_using_content = FileField(_l('Using Content'), validators=[DataRequired()])

    call_starting_point = FileField(_l('Call Start Point'), validators=[DataRequired()])
    third_party_packages = FileField(_l('Third Party Package'), validators=[DataRequired()])

    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class AddRoleForm(FlaskForm):
    def __init__(self, original_role_name, *args, **kwargs):
        super(AddRoleForm, self).__init__(*args, **kwargs)
        self.original_role_name = original_role_name

    def validate_role_name(self, role_name):
        if role_name.data != self.original_role_name:
            role_entity = SaasRole.query.filter_by(name=self.role_name.data).first()
            if role_entity is not None:
                raise ValidationError(_('Please use a different role name.'))

    role_name = StringField(_l('Role Name'), validators=[DataRequired()], render_kw={"placeholder": _('Role Name')})
    creator = StringField(_l('Creator'), validators=[DataRequired()], render_kw={'readonly':'readonly'})
    app_name = StringField(_l('App Name'), validators=[DataRequired()], render_kw={'readonly':'readonly'})

    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})

class AddUserForm(FlaskForm):
    def __init__(self, original_user_name, *args, **kwargs):
        super(AddUserForm, self).__init__(*args, **kwargs)
        self.original_user_name = original_user_name

    def validate_user_name(self, user_name):
        if user_name.data != self.original_user_name:
            user_entity = SaasUser.query.filter_by(name=self.user_name.data).first()
            if user_entity is not None:
                raise ValidationError(_('Please use a different user name.'))

    def query_factory(self=None):
        return [r.name for r in SaasRole.query.all()]

    def get_pk(obj):
        return obj

    user_name = StringField(_l('User Name'), validators=[DataRequired()], render_kw={"placeholder": _('User Name')})
    user_password = PasswordField(_l('Password'),
                                       description='In edit mode, set null in this field means no modification for current password.',
                                       render_kw={"placeholder": _('Password')})
    role_list = QuerySelectField(label=_l('Role'), validators=[DataRequired()], query_factory=query_factory,
                                get_pk=get_pk, default='Please choose')
    creator = StringField(_l('Creator'), validators=[DataRequired()], render_kw={'readonly':'readonly'})
    app_name = StringField(_l('App'), validators=[DataRequired()], render_kw={'readonly':'readonly'})
    submit = SubmitField(_l('Save'), render_kw={"id": "submitButton"})