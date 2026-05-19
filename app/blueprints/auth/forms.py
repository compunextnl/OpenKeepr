from __future__ import annotations

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    Regexp,
)


class LoginForm(FlaskForm):
    email = StringField(_l("Email"), validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(_l("Password"), validators=[DataRequired(), Length(max=255)])
    remember = BooleanField(_l("Remember me"))
    submit = SubmitField(_l("Sign in"))


class TwoFactorForm(FlaskForm):
    token = StringField(
        _l("6-digit code"),
        validators=[DataRequired(), Length(min=6, max=8), Regexp(r"^\d{6,8}$|^[a-z0-9-]{10,}$")],
    )
    submit = SubmitField(_l("Verify"))


class RegisterForm(FlaskForm):
    email = StringField(_l("Email"), validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        _l("Password"),
        validators=[DataRequired(), Length(min=12, max=255, message=_l("Use at least 12 characters."))],
    )
    confirm = PasswordField(
        _l("Confirm password"),
        validators=[DataRequired(), EqualTo("password", message=_l("Passwords must match."))],
    )
    submit = SubmitField(_l("Create account"))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l("Current password"), validators=[DataRequired()])
    new_password = PasswordField(
        _l("New password"),
        validators=[DataRequired(), Length(min=12, max=255)],
    )
    confirm = PasswordField(
        _l("Confirm new password"),
        validators=[DataRequired(), EqualTo("new_password", message=_l("Passwords must match."))],
    )
    submit = SubmitField(_l("Update password"))


class Enable2FAForm(FlaskForm):
    token = StringField(_l("6-digit code"), validators=[DataRequired(), Length(min=6, max=6), Regexp(r"^\d{6}$")])
    submit = SubmitField(_l("Enable two-factor authentication"))
