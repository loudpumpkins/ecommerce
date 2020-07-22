"""
DJango Finite State Machine.

Control the state of a model when the sequence is crucial such as:
Draft -> Approval -> Publish

In the above example, DJango state machine won't allow you to publish an
article if it has not yet been approved or even draft.


Usage example:

    from shared.statemachine import FSMField, transition

    >> in models.py

    state = FSMField(
        default=State.DRAFT,
        verbose_name='Publication State',
        choices=State.CHOICES,
        protected=True, #  protected by default
    )

    def can_display(self):
        if 'condition met'
            return True
        return False

    @transition(field=state, source=[State.APPROVED, State.EXPIRED],
        target=State.PUBLISHED, conditions=[can_display])
    def publish(self):
        '''
        Publish the object.
        '''

full usage example on an entire model.py on github:
https://github.com/gadventures/django-fsm-admin/blob/master/example/fsm_example/models.py

"""
import inspect
from functools import partialmethod, wraps
import sys

from django.apps import apps as django_apps
from django.db import models
from django.db.models.signals import class_prepared
from django.dispatch import Signal


pre_transition = Signal(providing_args=['instance', 'name', 'source', 'target'])
post_transition = Signal(providing_args=['instance', 'name', 'source', 'target', 'exception'])


def get_model(app_label, model_name):
    app = django_apps.get_app_config(app_label)
    return app.get_model(model_name)


class TransitionNotAllowed(Exception):
    """Raised when a transition is not allowed"""

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('object', None)
        self.method = kwargs.pop('method', None)
        super(TransitionNotAllowed, self).__init__(*args, **kwargs)


class InvalidResultState(Exception):
    """Raised when we got invalid result state"""


class Transition(object):
    def __init__(self, method, source, target, on_error, conditions, permission, custom):
        self.method = method
        self.source = source
        self.target = target
        self.on_error = on_error
        self.conditions = conditions
        self.permission = permission
        self.custom = custom

    @property
    def name(self):
        return self.method.__name__

    def has_perm(self, instance, user):
        if not self.permission:
            return True
        elif callable(self.permission):
            return bool(self.permission(instance, user))
        elif user.has_perm(self.permission, instance):
            return True
        elif user.has_perm(self.permission):
            return True
        else:
            return False


def get_available_FIELD_transitions(instance, field):
    """
    List of transitions available in current model state
    with all conditions met
    """
    curr_state = field.get_state(instance)
    transitions = field.transitions[instance.__class__]

    for name, transition in transitions.items():
        meta = transition._django_fsm
        if meta.has_transition(curr_state) and meta.conditions_met(instance, curr_state):
            yield meta.get_transition(curr_state)


def get_all_FIELD_transitions(instance, field):
    """
    List of all transitions available in current model state
    """
    return field.get_all_transitions(instance.__class__)


def get_available_user_FIELD_transitions(instance, user, field):
    """
    List of transitions available in current model state
    with all conditions met and user have rights on it
    """
    for transition in get_available_FIELD_transitions(instance, field):
        if transition.has_perm(instance, user):
            yield transition


class FSMMeta(object):
    """
    Models methods transitions meta information
    """
    def __init__(self, field, method):
        self.field = field
        self.transitions = {}  # source -> Transition

    def get_transition(self, source):
        transition = self.transitions.get(source, None)
        if transition is None:
            transition = self.transitions.get('*', None)
        if transition is None:
            transition = self.transitions.get('+', None)
        return transition

    def add_transition(self, method, source, target, on_error=None, conditions=[], permission=None, custom={}):
        if source in self.transitions:
            raise AssertionError('Duplicate transition for {0} state'.format(source))

        self.transitions[source] = Transition(
            method=method,
            source=source,
            target=target,
            on_error=on_error,
            conditions=conditions,
            permission=permission,
            custom=custom)

    def has_transition(self, state):
        """
        Lookup if any transition exists from current model state using current method
        """
        if state in self.transitions:
            return True

        if '*' in self.transitions:
            return True

        if '+' in self.transitions and self.transitions['+'].target != state:
            return True

        return False

    def conditions_met(self, instance, state):
        """
        Check if all conditions have been met
        """
        transition = self.get_transition(state)

        if transition is None:
            return False
        elif transition.conditions is None:
            return True
        else:
            return all(map(lambda condition: condition(instance), transition.conditions))

    def has_transition_perm(self, instance, state, user):
        transition = self.get_transition(state)

        if not transition:
            return False
        else:
            return transition.has_perm(instance, user)

    def next_state(self, current_state):
        transition = self.get_transition(current_state)

        if transition is None:
            raise TransitionNotAllowed('No transition from {0}'.format(current_state))

        return transition.target

    def exception_state(self, current_state):
        transition = self.get_transition(current_state)

        if transition is None:
            raise TransitionNotAllowed('No transition from {0}'.format(current_state))

        return transition.on_error


class FSMFieldDescriptor(object):
    """
    Disallow direct modification of states
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        return self.field.get_state(instance)

    def __set__(self, instance, value):
        if self.field.protected and self.field.name in instance.__dict__:
            raise AttributeError('Direct {0} modification is not allowed'.format(self.field.name))

        # Update state
        self.field.set_proxy(instance, value)
        self.field.set_state(instance, value)


class FSMFieldMixin(object):
    descriptor_class = FSMFieldDescriptor

    def __init__(self, *args, **kwargs):
        self.protected = kwargs.pop('protected', True)
        self.transitions = {}  # cls -> (transitions name -> method)
        self.state_proxy = {}  # state -> ProxyClsRef

        state_choices = kwargs.pop('state_choices', None)
        choices = kwargs.get('choices', None)
        if state_choices is not None and choices is not None:
            raise ValueError('Use one of choices or state_choices value')

        if state_choices is not None:
            choices = []
            for state, title, proxy_cls_ref in state_choices:
                choices.append((state, title))
                self.state_proxy[state] = proxy_cls_ref
            kwargs['choices'] = choices

        super(FSMFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(FSMFieldMixin, self).deconstruct()
        if self.protected:
            kwargs['protected'] = self.protected
        return name, path, args, kwargs

    def get_state(self, instance):
        return instance.__dict__[self.name]

    def set_state(self, instance, state):
        instance.__dict__[self.name] = state

    def set_proxy(self, instance, state):
        """
        Change class
        """
        if state in self.state_proxy:
            state_proxy = self.state_proxy[state]

            try:
                app_label, model_name = state_proxy.split(".")
            except ValueError:
                # If we can't split, assume a model in current app
                app_label = instance._meta.app_label
                model_name = state_proxy

            model = get_model(app_label, model_name)
            if model is None:
                raise ValueError('No model found {0}'.format(state_proxy))

            instance.__class__ = model

    def change_state(self, instance, method, *args, **kwargs):
        meta = method._django_fsm
        method_name = method.__name__
        current_state = self.get_state(instance)

        if not meta.has_transition(current_state):
            raise TransitionNotAllowed(
                "Can't switch from state '{0}' using method '{1}'".format(current_state, method_name),
                object=instance, method=method)
        if not meta.conditions_met(instance, current_state):
            raise TransitionNotAllowed(
                "Transition conditions have not been met for method '{0}'".format(method_name),
                object=instance, method=method)

        next_state = meta.next_state(current_state)

        signal_kwargs = {
            'sender': instance.__class__,
            'instance': instance,
            'name': method_name,
            'field': meta.field,
            'source': current_state,
            'target': next_state,
            'method_args': args,
            'method_kwargs': kwargs
        }

        pre_transition.send(**signal_kwargs)

        try:
            result = method(instance, *args, **kwargs)
            if next_state is not None:
                if hasattr(next_state, 'get_state'):
                    next_state = next_state.get_state(
                        instance, transition, result,
                        args=args, kwargs=kwargs)
                    signal_kwargs['target'] = next_state
                self.set_proxy(instance, next_state)
                self.set_state(instance, next_state)
        except Exception as exc:
            exception_state = meta.exception_state(current_state)
            if exception_state:
                self.set_proxy(instance, exception_state)
                self.set_state(instance, exception_state)
                signal_kwargs['target'] = exception_state
                signal_kwargs['exception'] = exc
                post_transition.send(**signal_kwargs)
            raise
        else:
            post_transition.send(**signal_kwargs)

        return result

    def get_all_transitions(self, instance_cls):
        """
        Returns [(source, target, name, method)] for all field transitions
        """
        transitions = self.transitions[instance_cls]

        for name, transition in transitions.items():
            meta = transition._django_fsm

            for transition in meta.transitions.values():
                yield transition

    def contribute_to_class(self, cls, name, **kwargs):
        self.base_cls = cls

        super(FSMFieldMixin, self).contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, self.descriptor_class(self))
        setattr(cls, 'get_all_{0}_transitions'.format(self.name),
                partialmethod(get_all_FIELD_transitions, field=self))
        setattr(cls, 'get_available_{0}_transitions'.format(self.name),
                partialmethod(get_available_FIELD_transitions, field=self))
        setattr(cls, 'get_available_user_{0}_transitions'.format(self.name),
                partialmethod(get_available_user_FIELD_transitions, field=self))

        class_prepared.connect(self._collect_transitions)

    def _collect_transitions(self, *args, **kwargs):
        sender = kwargs['sender']

        if not issubclass(sender, self.base_cls):
            return

        def is_field_transition_method(attr):
            return (inspect.ismethod(attr) or inspect.isfunction(attr)) \
                and hasattr(attr, '_django_fsm') \
                and attr._django_fsm.field in [self, self.name]

        sender_transitions = {}
        transitions = inspect.getmembers(sender, predicate=is_field_transition_method)
        for method_name, method in transitions:
            method._django_fsm.field = self
            sender_transitions[method_name] = method

        self.transitions[sender] = sender_transitions


class FSMField(FSMFieldMixin, models.CharField):
    """
    State Machine support for Django model as CharField
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 50)
        super(FSMField, self).__init__(*args, **kwargs)


def transition(field, source='*', target=None, on_error=None, conditions=[], permission=None, custom={}):
    """
    Method decorator to mark allowed transitions.

    Set target to None if current state needs to be validated and
    has not changed after the function call.
    """
    def inner_transition(func):
        wrapper_installed, fsm_meta = True, getattr(func, '_django_fsm', None)
        if not fsm_meta:
            wrapper_installed = False
            fsm_meta = FSMMeta(field=field, method=func)
            setattr(func, '_django_fsm', fsm_meta)

        if isinstance(source, (list, tuple, set)):
            for state in source:
                func._django_fsm.add_transition(func, state, target, on_error, conditions, permission, custom)
        else:
            func._django_fsm.add_transition(func, source, target, on_error, conditions, permission, custom)

        @wraps(func)
        def _change_state(instance, *args, **kwargs):
            return fsm_meta.field.change_state(instance, func, *args, **kwargs)

        if not wrapper_installed:
            return _change_state

        return func

    return inner_transition


class State(object):
    def get_state(self, model, transition, result, args=[], kwargs={}):
        raise NotImplementedError


class RETURN_VALUE(State):
    def __init__(self, *allowed_states):
        self.allowed_states = allowed_states if allowed_states else None

    def get_state(self, model, transition, result, args=[], kwargs={}):
        if self.allowed_states is not None:
            if result not in self.allowed_states:
                raise InvalidResultState(
                    '{} is not in list of allowed states\n{}'.format(
                        result, self.allowed_states))
        return result
