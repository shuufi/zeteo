"""Operations for application-wide business settings."""

from sqlmodel import Session

from backend.application.models import AppSettings
from backend.calendar.models import Period, PeriodType


SETTINGS_ID = 1


def current_actual_period(session: Session) -> str | None:
    settings = session.get(AppSettings, SETTINGS_ID)
    return settings.current_actual_period_code if settings else None


def set_current_actual_period(session: Session, period_code: str) -> None:
    period = session.get(Period, period_code)
    if period is None or period.period_type != PeriodType.MONTH:
        raise ValueError(f"Current Actual Period must be a Zeteo Month; got {period_code!r}.")
    settings = session.get(AppSettings, SETTINGS_ID)
    if settings is None:
        session.add(AppSettings(id=SETTINGS_ID, current_actual_period_code=period_code))
    else:
        settings.current_actual_period_code = period_code
        session.add(settings)
    session.commit()
