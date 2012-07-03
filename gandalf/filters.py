from __future__ import with_statement

import hashlib
import os
import operator

from gandalf.config import current_logged_in_identity_string

class BridgeFilter(object):
    name = None
    filename = None

    @staticmethod
    def _matches(context, identity):
        raise NotImplementedError("This filter needs to implement a '_matches' method")

    @classmethod
    def passes_filter(cls, filter, identity):
        return cls._matches(filter.context, identity) and filter.percentage > BridgeFilter._identity_percentage(filter.key())

    @staticmethod
    def _identity_percentage(key):
        sig = hashlib.md5(str(key) + current_logged_in_identity_string()).hexdigest()
        return int(sig, base=16) % 100

    @staticmethod
    def initial_context():
        return {}

    @classmethod
    def find_subclass(cls, filter_type):
        for subclass in cls.__subclasses__():
            if subclass.name == filter_type:
                return subclass

    @classmethod
    def get_filter_types(cls):
        return [{
            'proper_name': subclass.proper_name(),
            'name': subclass.name,
        } for subclass in cls.__subclasses__()]

    @classmethod
    def proper_name(cls):
        return cls.name.replace("-", " ").capitalize()

    @classmethod
    def render(cls):
        if not cls.filename:
            return ""

        path = os.path.join(os.path.dirname(__file__), "templates/filters/%s" % cls.filename)

        with open(path) as f:
            html = f.read()

        return html


class IsDeveloperFilter(BridgeFilter):
    name = "is-developer"

    @staticmethod
    def _matches(context, identity):
        return identity.developer


class AllUsersBridgeFilter(BridgeFilter):
    name = "all-users"

    @staticmethod
    def _matches(context, identity):
        return True


class NumberOfProficientExercisesBridgeFilter(BridgeFilter):
    name = "number-of-proficient-exercises"
    filename = "number-of-proficient-exercises.html"

    @staticmethod
    def _matches(context, identity):
        number_of_proficiencies = len(identity.all_proficient_exercises)

        try:
            exercises = int(context['exercises'])
        except ValueError:
            return False

        return {'=': operator.eq, '>=': operator.ge, '<=': operator.le}[context['comp']](
            number_of_proficiencies,
            exercises,
        )

    @staticmethod
    def initial_context():
        return {
            'comp': "<=",
            'exercises': "0",
        }


class HasCoachBridgeFilter(BridgeFilter):
    name = "has-coach"
    filename = "has-coach.html"

    @staticmethod
    def _matches(context, identity):
        has_coach = bool(identity.coaches)

        should_have_coach = context['coach'] == "1"

        return should_have_coach == has_coach

    @staticmethod
    def initial_context():
        return {
            'coach': "1",
        }


class SpecificCoachesBridgeFilter(BridgeFilter):
    name = "specific-coaches"
    filename = "specific-coaches.html"

    @staticmethod
    def _matches(context, identity):
        coaches_to_have = context['coaches'].split()

        return bool(set(coaches_to_have) & set(identity.coaches))

    @staticmethod
    def initial_context():
        return {
            'coaches': "",
        }
