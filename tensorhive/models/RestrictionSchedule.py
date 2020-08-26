import re
import datetime
import logging

from sqlalchemy import Column, Integer, String, Time, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from tensorhive.database import Base
from tensorhive.models.CRUDModel import CRUDModel
from tensorhive.utils.Weekday import Weekday
from typing import List, Union

log = logging.getLogger(__name__)


class RestrictionSchedule(CRUDModel, Base):  # type: ignore
    """
    Class representing restriction schedules.
    One schedule is able to specify same start and end hours for specified days of the week.
    If one would want to use different hours for different days, he would need to create separate schedules for these
    hours.
    For example, if one wants to create schedule active on Mondays and Wednesdays between 8 and 11 am and on Tuesdays
    between 2 and 4 am, he would need to create two schedules:
    - Schedule A - schedule_days=13, hour_start=datetime.time(8, 0, 0), datetime.time=Time(11, 0, 0)
    - Schedule B = schedule_days=2, hour_start=datetime.time(2, 0, 0), datetime.time=Time(4, 0, 0)

    Note: All times and dates used are UTC.
    """
    __tablename__ = 'restriction_schedules'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    _schedule_days = Column(String(7), nullable=False)
    hour_start = Column(Time(), nullable=False)
    hour_end = Column(Time(), nullable=False)

    _restrictions = relationship('Restriction', secondary='restriction2schedule')

    def __init__(self, schedule_days: Union[List[Weekday], str], hour_start: datetime.time, hour_end: datetime.time):
        self.schedule_days = schedule_days
        self.hour_start = hour_start
        self.hour_end = hour_end

    def __repr__(self):
        return '''<RestrictionSchedule id={id}
            schedule_days={schedule_days}
            hour_start={hour_start}
            hour_end={hour_end}'''\
            .format(id=self.id, schedule_days=self.schedule_days, hour_start=self.hour_start, hour_end=self.hour_end)

    def check_assertions(self):
        assert self.is_valid_schedule_expression(self.schedule_days), '''
        schedule_days does not contain valid schedule expression - it should consist of numbers from 1 to 7 inclusive,
        each representing day of the week that the schedule is valid on (1 - Monday, 2 - Tuesday, ..., 7 - Sunday).
        '''
        assert self.hour_end > self.hour_start, 'End hour cannot happen before start hour!'

    @hybrid_property
    def schedule_days(self):
        return self._schedule_days

    @hybrid_property
    def restrictions(self):
        return self._restrictions

    @schedule_days.setter
    def schedule_days(self, days: Union[List[Weekday], str]):
        if isinstance(days, str):
            self._schedule_days = (''.join(sorted(days)))
        else:
            self._schedule_days = self.parse_schedule_list(days)

    @property
    def is_active(self):
        today = str(datetime.datetime.utcnow().date().weekday() + 1)  # weekday uses 0-6 for day numbering, we use 1-7
        now = datetime.datetime.utcnow().time()
        return today in self.schedule_days and self.hour_start <= now < self.hour_end

    @staticmethod
    def is_valid_schedule_expression(schedule_expression):
        has_repeating_characters = len(set(i for i in schedule_expression if schedule_expression.count(i) > 1)) > 0
        regex_match = re.fullmatch('[1-7]{1,7}', schedule_expression) is not None
        return regex_match and not has_repeating_characters

    @property
    def as_dict(self):
        return {
            'id': self.id,
            'scheduleDays': self.parse_schedule_string(self.schedule_days),
            'hourStart': self.hour_start.strftime('%H:%M'),
            'hourEnd': self.hour_end.strftime('%H:%M')
        }

    @staticmethod
    def parse_schedule_string(schedule: str) -> List[Weekday]:
        return [Weekday(int(day)) for day in sorted(schedule)]

    @staticmethod
    def parse_schedule_list(schedule: List[Weekday]) -> str:
        return ''.join((sorted(''.join([str(day.value) for day in schedule]))))


class Restriction2Schedule(Base):  # type: ignore
    __tablename__ = 'restriction2schedule'
    __tableargs__ = {'sqlite_autoincrement': True}

    restriction_id = Column(Integer, ForeignKey('restrictions.id', ondelete='CASCADE'), primary_key=True)
    schedule_id = Column(Integer, ForeignKey('restriction_schedules.id', ondelete='CASCADE'), primary_key=True)

    restriction = relationship('Restriction',
                               backref=backref('restriction2schedule', cascade='all,delete-orphan'))
    schedule = relationship('RestrictionSchedule',
                            backref=backref('restriction2schedule', cascade='all,delete-orphan'))