from __future__ import annotations

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.models.feedback import FEEDBACK_TYPES


class FeedbackForm(FlaskForm):
    type = SelectField(
        _l("Type"),
        choices=[(t, t) for t in FEEDBACK_TYPES],
        default="other",
    )
    message = TextAreaField(
        _l("Your feedback"),
        validators=[DataRequired(), Length(min=4, max=5000)],
    )
    contact = StringField(
        _l("Reply address (optional)"),
        validators=[Optional(), Email(), Length(max=255)],
    )
    # Honeypot field — bots fill in everything; humans don't see it.
    website = HiddenField()
    submit = SubmitField(_l("Send feedback"))
