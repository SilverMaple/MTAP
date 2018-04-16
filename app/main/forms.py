# -*- coding: utf-8 -*-
# @Time    : 2018/4/9 14:52:41
# @Author  : SilverMaple
# @Site    : https://github.com/SilverMaple
# @File    : forms.py

from flask import request
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SubmitField, TextAreaField, FileField, BooleanField, PasswordField, SelectField
from wtforms.validators import ValidationError, DataRequired, Length
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from flask_babel import _, lazy_gettext as _l
from app.models import User, App, AppExpand, AppAdmin, Tenant


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