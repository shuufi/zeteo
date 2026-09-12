"""Operations for application-wide business settings."""

from sqlmodel import Session

from backend.application.models import AppSettings
from backend.calendar.models import Period, Year


SETTINGS_ID = 1


def current_actual_period(session: Session) -> tuple[int, int] | None:
    settings = session.get(AppSettings, SETTINGS_ID)
    if settings is None or settings.current_actual_year is None or settings.current_actual_period is None:
        return None
    return settings.current_actual_year, settings.current_actual_period


def set_current_actual_period(session: Session, year: int, period: int) -> None:
    if session.get(Year, year) is None:
        raise ValueError(f"Current Actual Period must be a known fiscal Year; got {year!r}.")
    if session.get(Period, period) is None:
        raise ValueError(f"Current Actual Period must be a Zeteo Period (1-12); got {period!r}.")
    settings = session.get(AppSettings, SETTINGS_ID)
    if settings is None:
        session.add(AppSettings(id=SETTINGS_ID, current_actual_year=year, current_actual_period=period))
    else:
        settings.current_actual_year = year
        settings.current_actual_period = period
        session.add(settings)
    session.commit()
