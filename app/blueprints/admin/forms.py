from __future__ import annotations

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional


class SettingsForm(FlaskForm):
    maintenance_mode = BooleanField(_l("Maintenance mode"))
    maintenance_message = TextAreaField(_l("Maintenance message"), validators=[Optional(), Length(max=500)])
    banner_text = StringField(_l("Banner text"), validators=[Optional(), Length(max=300)])
    banner_level = SelectField(
        _l("Banner level"),
        choices=[("", "—"), ("info", "info"), ("warning", "warning"), ("danger", "danger")],
        validators=[Optional()],
    )
    public_login_enabled = BooleanField(_l("Enable public login page"))
    public_registration_enabled = BooleanField(_l("Allow new user registrations"))
    api_enabled = BooleanField(_l("Expose REST API and /docs/api"))
    submit = SubmitField(_l("Save settings"))


class TestEmailForm(FlaskForm):
    to_email = StringField(_l("Send test e-mail to"), validators=[Optional(), Length(max=255)])
    submit = SubmitField(_l("Send test e-mail"))


class FeedbackUpdateForm(FlaskForm):
    status = SelectField(
        _l("Status"),
        choices=[("new", "new"), ("in_progress", "in_progress"), ("resolved", "resolved"), ("spam", "spam")],
    )
    admin_notes = TextAreaField(_l("Notes"), validators=[Optional(), Length(max=2000)])
    submit = SubmitField(_l("Update"))
