import json
import logging

from .event_dispatcher import EventDispatcher
from .sccertificate import SCCertificate, NullCertificateError
from .scsession import get_common_algorithm, SCSession
from ..utils import verify_str

class BaseDevice():
    """BaseDevice(stop_event, **kwargs) -> BaseDevice

    This class is the central hub of the device. It both stores information
    about the device, and handles requests made to the device

    Additionally, this class supports `lazy initialization` of the form
    class BaseDevice(Service):
        name = ...
        device_type = ...
        namespace = ...
        mac_address = ...
        services = ...
        pref_alg = ... 

    All attributes, other than pref_alg, are required
    `services` should be an array of all the services that this device implements
    `pref_alg` is optional and should be the name of the preferred hashing
        algorithm (ex. sha256)
    """
    def __init__(self, stop, **kwargs):
        fields = (
            "name", "device_type", "namespace",
            "mac_address", "services", "pref_alg"
        )
        for k, v in kwargs.items():
            if k not in fields:
                raise AttributeError("Invalid field `%s`" % k)
            setattr(self, k, v)
        for field in fields:
            if getattr(self, field, None) is None:
                if field == "pref_alg":
                    self.pref_alg = None
                else:
                    raise AttributeError("Expected value for `%s`" % field)
            elif (field == "device_type" or field == "namespace"
                    or field == "name"):
                verify_str(getattr(self, field), field)
        self.spec_url = "setup.json"
        self.urn = "urn:%s:device:%s:1" % (
            self.namespace,
            self.device_type.lower()
        )
        self.sessions = {}
        self.dispatcher = EventDispatcher(stop)
        self.service_methods = {}
        self.service_events = {}
        # maybe make these lists rather than dicts and add get_method_by_name
        # to the service class (where these are already seperated into dicts)
        for svc in self.services:
            svc.add_dispatcher(self.dispatcher)
            self.service_methods[svc.control_url] = svc
            self.service_events[svc.event_url] = svc

    def values_dict(self):
        """Returns a dict of device-defining data"""
        return dict(
            name=self.name,
            device_type=self.device_type,
            urn=self.urn,
            mac_address=self.mac_address,
            services={
                service.name: dict(
                    spec_url=service.spec_url,
                    control_url=service.control_url,
                    event_url=service.event_url,
                )
                for service in self.services
            }
        )

    def __str__(self):
        return str(self.values_dict())

    def get_service_ptr(self, svc_name):
        """get_service_ptr(svc_name_str) -> int

        Returns the index of the first service with name, `name`
        """
        for i, svc in enumerate(self.services):
            if svc.name == svc_name:
                return i
        raise ValueError("%s not found" % svc_name)

    def handle_request(self, uuid, serverclient):
        """handle_request(uuid_str, serverclient)

        Handles one http request from an authenticated host and attempts to run
        the requested service method

        Writes --
            401 in cases where message decryption fails
            501 in cases where the service method is not found
            500 in cases where an unknown error occurs
        """
        try:
            if uuid not in self.sessions:
                serverclient.write_head(401)
                return
            session = self.sessions[uuid]
            service_url = serverclient.req.url
            body = session.decrypt(serverclient.req.body)
            method, args = json.loads(body)
            service = self.service_methods[service_url]
            method = service.methods[method]
            output = method.main(self, args)
            session.update_key()
            body = session.encrypt(json.dumps(output))
            serverclient.write_body(
                200,
                "application/octet-stream",
                body
            )
        except (UnicodeDecodeError, ValueError):
            serverclient.write_head(401)
        except KeyError:
            serverclient.write_head(501)
        except Exception as e:
            logging.error(e)
            serverclient.write_head(500)

    def add_subscriber(self, uuid, serverclient):
        """add_subscriber(uuid_str, serverclient)

        Handles one http request from an authenticated host and attempts to add
        the host as a subscriber to the event_url

        At present, this takes no arguments from the host, but the host should
        still send something to prove their authenticity.

        Writes --
            401 in cases where message decryption fails
            501 in cases where the service event_url is not found
            500 in cases where an unknown error occurs
        """
        try:
            event_url = serverclient.req.url
            logging.debug(event_url)
            if uuid not in self.sessions:
                serverclient.write_head(401)
                return
            elif event_url not in self.service_events:
                serverclient.write_head(501)
                return
            session = self.sessions[uuid]
            args = json.loads(session.decrypt(serverclient.req.body))
            self.dispatcher.add_subscriber(
                event_url,
                (serverclient.ip, args["port"])
            )
            session.update_key()
            serverclient.write_head(200)
        except (UnicodeDecodeError, ValueError):
            serverclient.write_head(401)
        except Exception as e:
            logging.error(e)
            serverclient.write_head(500)

    def create_session(self, uuid, serverclient):
        """create_session(uuid_str, serverclient)

        Handles one http request from an unauthenticated host and attempts
        to begin an authenticated session with the host.

        Writes --
            401 in cases where invalid arguments are sent and, in addition,
                conveys what argument was invalid
            500 in cases where an unknown error occurs
        """
        try:
            body = serverclient.req.body.decode("utf-8")
            session_args = json.loads(body)
            cert = SCCertificate(uuid, session_args["offset"])
            algorithm = get_common_algorithm(
                session_args["algorithms"], self.pref_alg
            )
            serverclient.write_body(
                200,
                "text/plain; charset=utf-8",
                algorithm
            )
            self.sessions[uuid] = SCSession(cert, algorithm)
        except KeyError as ke:
            serverclient.write_body(
                401,
                "application/json",
                json.dumps(dict(missing=ke.message))
            )
        except NullCertificateError as nce:
            serverclient.write_body(
                401,
                "application/json",
                json.dumps(dict(missing="certificate"))
            )
        except Exception as e:
            logging.error(e)
            serverclient.write_head(500)
