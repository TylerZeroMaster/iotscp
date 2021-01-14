import json

from ..utils import verify_str

_default_icon = "icon.gif"

class ServiceArgError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ServiceArg(tuple):
    """ServiceArg(name_str, type_str) -> ServiceArg

    This class is used to define what types a service method can accept or
    return, and what types a service event can send
    """
    # define concrete types
    # the strings represent types that all devices should support
    __type_map = {
        bool: "bool",
        dict: "map",
        float: "float",
        int: "int",
        list: "list",
        str: "string",
    }
    def __init__(self, name, type):
        if type not in self.__type_map:
            raise ServiceArgError("Type %s is not supported" % type)
        self.name = name
        self.type = type

    def __new__(cls, name, type):
        return tuple.__new__(cls, (name, type))

    def __str__(self):
        return "%s: %s" % (self.name, self.__type_map[self.type])

    def __repr__(self):
        return "ServiceArg(name=%s, type=%s)" % (self.name, self.type)

class ServiceMethodError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ServiceMethod():
    """ServiceMethod(
        name_str,
        thunk_func,
        args_list[ServiceArg],
        returns_list[ServiceArg]
    ) -> ServiceMethod

    A service method is something that can be called by network hosts that have
    authenticated with this device.

    thunk is the function that will be executed when this method is called,
    args is a list of ServiceArgs that thunk accepts
    returns is a list of ServiceArgs that thunk returns

    thunk should take the form:
    def whatever_you_name_it(device, kwargs):
        ...
        ...
        return dict(your_service_arg_name=your_service_arg_value)
    """
    def __init__(self, name, thunk, args=None, returns=None, doc=""):
        if args is None:
            args = []
        elif isinstance(args, ServiceArg):
            args = [args]
        if returns is None:
            returns = []
        elif isinstance(returns, ServiceArg):
            returns = [returns]
        self.name = name
        self.thunk = thunk
        self.args = args
        self.returns = returns
        self.__doc__ = doc

    def verify_output(self, output):
        """verify_output(output_dict)

        This ensures that the service method returns what it is supposed to.

        In the future, it would be nice to use dis to check each method's
        output only once, rather than at every call, but, for now, this
        seems to be the best solution.

        Raises ServiceMethodError if the output is incorrect
        """
        if output is not None:
            for svcarg in self.returns:
                arg, _type = svcarg
                if arg not in output:
                    raise ServiceMethodError(
                        "Missing return value: %s" % arg
                    )
                elif not isinstance(output[arg], _type):
                    raise ServiceMethodError(
                        ("Type mismatch error at `%s`: expected %s, got %s"
                        " in return value") % (arg, _type, type(output[arg]))
                    )
        else:
            raise ServiceMethodError(
                "Expected return value from %s" % self.name
            )

    def main(self, device, args_dict):
        """Calls the service method's thunk"""
        for arg, _type in self.args:
            if arg not in args_dict:
                raise ServiceArgError("Missing arguments: %s" % arg)
            elif not isinstance(arg, _type):
                raise ServiceArgError(
                    "Type mismatch error at `%s`: expected %s, got %s"
                    % (arg, _type, type(arg))
                )
        output = self.thunk(device, **args_dict)
        if self.returns is not None:
            self.verify_output(output)
        # returns None if thunk returns nothing
        return output

    def values_dict(self):
        """Returns a dict of ServiceMethod-defining data"""
        return dict(
            name=self.name,
            args=list(map(str, self.args)),
            returns=list(map(str, self.returns)),
            doc=self.__doc__,
        )

    def __str__(self):
        return str(self.values_dict())

    def __repr__(self):
        return ("ServiceMethod { name: %s, args: %s }"
                % (self.name, list(map(repr, self.args))))

class ServiceEvent():
    """ServiceEvent(name_str, sends_list[ServiceArg]) -> ServiceEvent

    A ServiceEvent is something that an authenticated host can subscribe to, to
    recv updates from the device as its state changes
    """
    def __init__(self, name, sends, doc=""):
        self.name = name
        if isinstance(sends, ServiceArg):
            sends = [sends]
        self.sends = {arg.name: arg for arg in sends}
        self.__doc__ = doc

    def validate(self, kwargs):
        """validate(**kwargs)

        This is used externally by the Service class to ensure that sent events
        match their definition
        """
        for k, arg in kwargs.items():
            if not k in self.sends:
                raise ServiceArgError("Invalid event argument `%s`" % k)
            else:
                _type = self.sends[k].type
                if not isinstance(arg, _type):
                    raise ServiceArgError(
                        "Type mismatch error at `%s`: expected %s, got %s"
                        % (k, _type, type(arg))
                    )

    def values_dict(self):
        """Returns a dict of ServiceEvent-defining data"""
        return dict(
            name=self.name,
            sends=list(map(str, self.sends.values())),
            doc=self.__doc__,
        )

    def __str__(self):
        return str(self.values_dict())

    def __repr__(self):
        return ("ServiceEvent { name: %s, sends: %s }"
                % (self.name, list(map(repr, self.sends.values()))))

class Service():
    """Service(**kwargs) -> Service

    A Service can encompass several service methods and service events. Each
    Service has a `control_url` and an `event_url`. The `control_url` is used
    to call methods, while the `event_url` is used when subscribing to events.

    `name`, `control_url`, and `event_url` are optional and default to
    '{CLASSNAME}', '/control/{CLASSNAME}/', and '/event/{CLASSNAME}/'
    respectively

    Additionally, this class supports lazy initialization of the form
    class MyService(Service):
        name = ...
        control_url = ...
        event_url = ...
        methods = ...
        events = ...

    All attributes are optional
    """
    def __init__(self, **kwargs):
        fields = (
            "name", "control_url", "event_url",
            "methods", "events"
        )
        for k, v in kwargs.items():
            if k not in fields:
                raise AttributeError("Invalid field `%s`" % k)
            setattr(self, k, v)
        for field in fields:
            field_value = getattr(self, field, None)
            if field_value is None:
                if field == "methods" or field == "events":
                    setattr(self, field, {})
                elif field == "name":
                    self.name = self.__class__.__name__
                elif field == "control_url":
                    self.control_url = ("/control/%s/"
                        % self.__class__.__name__.lower())
                elif field == "event_url":
                    self.event_url = ("/event/%s/"
                        % self.__class__.__name__.lower())
                else:
                    raise AttributeError("Expected value for `%s`" % field)
            elif field == "control_url" or field == "event_url":
                verify_str(field_value, field, whitelist=set("/"))
            elif field == "name":
                verify_str(field_value, field)
            elif field == "methods" or field == "events":
                setattr(self, field, {obj.name: obj for obj in field_value})
            self.spec_url = "%s.json" % self.name.lower()
        self.dispatcher = None

    def add_dispatcher(self, dispatcher):
        """Add a reference to the event dispatcher to this service.
        This should only be called by the device itself with a reference to the
        shutdown event because the dispatcher must know when the server is
        shutting down.
        """
        # For Rust, this will be a RWLock or a Mutex wrapped in Arc<>
        self.dispatcher = dispatcher

    def send_event(self, event_name, **kwargs):
        """send_event(event_name_str, **kwargs)

        Access this service's event dispatcher and send an event
        """
        # if the dispatcher is absent, the program should crash
        if self.event_url in self.dispatcher.subscribers:
            if event_name not in self.events:
                raise ValueError("Event name not found")
            self.events[event_name].validate(kwargs)
            kwargs["name"] = event_name
            self.dispatcher.send_event(self.event_url, kwargs)

    def values_dict(self):
        """Returns a dict of Service-defining data"""
        return dict(
            name=self.name,
            control_url=self.control_url,
            event_url=self.event_url,
            spec_url=self.spec_url,
            methods=[
                method.values_dict()
                for method in self.methods.values()
            ],
            events=[
                event.values_dict()
                for event in self.events.values()
            ],
        )

    def __str__(self):
        return str(self.values_dict())

    def __repr__(self):
        return repr(str(self))
