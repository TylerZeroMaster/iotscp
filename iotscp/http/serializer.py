import re
import os
import json
import logging
from hashlib import md5

from . import WEB_PATH

SERVICE_PATH = "services"

RE_VAR = re.compile("(`)(.+?)(`)")
SU_VAR = r"<code>\2</code>"

TEMPLATE_SIDE = '<div id="{name}"><a href="/{path}/{name}/">{name}</a></div>'

TEMPLATE_ARG = '<div class="inputoutput">{inner}</div>'
TEMPLATE_SERVICE_ITEM = """
    <div class="docblock">
        <h1 class="section-head">
            {serivce_type} {name}
        </h1>
        <div class="docstring">
            <div>
                Arguments:
            </div>
            <div class="inputsoutputs">
                {args}
            </div>
            <div>
                Returns:
            </div>
            <div class="inputsoutputs">
                {returns}
            </div>
            <pre>{docstring}</pre>
        </div>
    </div>
"""

TEMPLATE_DEV_INFO = """
    <div class="docblock">
        <h1 class="section-head">Device Information:</h1>
        <div class="docstring">
            <div>Name:</div>
            <div class="inputsoutputs">{device_name}</div>
            <div>Type:</div>
            <div class="inputsoutputs">{device_type}</div>
            <div>URN:</div>
            <div class="inputsoutputs">{urn}</div>
            <div>MAC address:</div>
            <div class="inputsoutputs">{mac_address}</div>
        </div>
    </div>
"""

TEMPLATE_SFW_INFO = """
    <div class="docblock">
        <h1 class="section-head">Software Information:</h1>
        <div class="docstring">
            <div>IOTSCP Version:</div>
            <div class="inputsoutputs">{version}</div>
        </div>
    </div>
"""

TEMPLATE_PAGE = """
<!DOCTYPE html>
<html>
    <head>
        <title>{title}</title>
        <link rel="stylesheet" type="text/css" media="all" href="/styles.css" />
    </head>
    <body>
        <div id="sidebar">
            <img src="/icon.png" alt="icon" width="100">
            <div id="Device Info"><a href="/">Device Info</a></div>
            {sidebar}
        </div>
        <div class="body">
            {body}
        </div>
        <script type="text/javascript">
            document.getElementById("{selected}").className = "selected";
        </script>
    </body>
</html>
"""

def _write_hashes(hashes):
    cachepath = os.path.join(WEB_PATH, "serializercache.json")
    with open(cachepath, "w") as fout:
        json.dump(hashes, fout)

def _load_hashes():
    cachepath = os.path.join(WEB_PATH, "serializercache.json")
    if os.path.exists(cachepath):
        with open(cachepath, "r") as fin:
            hashes = json.load(fin)
    else:
        hashes = []
    return hashes

def _get_hash(obj):
    return md5(str(obj).encode("utf-8")).hexdigest()

def write_file(path, content):
    """write_file(path_str, content_str)

    Write `content` to `path` after `path` has been joined to `WEB_PATH`
    """
    path = os.path.join(WEB_PATH, path)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "w") as fout:
        fout.write(content)

def create_docblock(service, serivce_type):
    """create_docblock(service_Service, serivce_type_str)

    Creates docblock that explains the service event or service method
    """
    name = service.name
    docstring = ""
    if serivce_type != "Service Event":
        args = '\n'.join(map(str, service.args))
        returns = '\n'.join(map(str, service.returns))
    else:
        args = ""
        returns = '\n'.join(map(str, service.sends.values()))
    if service.__doc__ != "":
        docstring = RE_VAR.sub(SU_VAR, service.__doc__)
    return TEMPLATE_SERVICE_ITEM.format(**locals())

def serialize_service(sidebar, device_name, service):
    """serialize_service(sidebar_str, device_name_str, service_Service)

    Serializes the service, creating the .json and .html representations of it
    """
    docstring = [
        create_docblock(method, "Service Method")
        for method in service.methods.values()
    ]
    docstring.extend((
        create_docblock(event, "Service Event")
        for event in service.events.values()
    ))
    docstring = TEMPLATE_PAGE.format(
        title=" - ".join((device_name, service.name)),
        selected=service.name,
        sidebar=sidebar,
        body='\n'.join(docstring)
    )
    write_file(
        os.path.join(
            SERVICE_PATH.replace('/', os.sep),
            service.name,
            "index.html"
        ),
        docstring
    )
    write_file(service.spec_url, json.dumps(service.values_dict()))

def serialize_device(sidebar, device):
    """serialize_device(sidebar_str, device_BaseDevice)

    Serializes the device, creating the .json and .html representations of it
    """
    body = '\n'.join((
        TEMPLATE_DEV_INFO.format(
            device_name=device.name,
            device_type=device.device_type,
            urn=device.urn,
            mac_address=device.mac_address
        ),
        # hard code this for now, but not in the future
        TEMPLATE_SFW_INFO.format(version="1.0")
    ))
    body = TEMPLATE_PAGE.format(
        title=" - ".join((device.name, "Device Info")),
        selected="Device Info",
        sidebar=sidebar,
        body=body
    )
    write_file("index.html", body)
    write_file("setup.json", json.dumps(device.values_dict()))

def create_side(services):
    """create_side(services_list[Service])

    Creates the sidebar for the web page
    """
    sidebar = (
        TEMPLATE_SIDE.format(path=SERVICE_PATH, name=svc.name)
        for svc in services
    )
    return '\n'.join(sidebar)

def serialize(device):
    """serialize(device_BaseDevice)

    Serializes all parts of the device into .json and .html representations
    """
    old_hashes = _load_hashes()
    new_hashes = []
    sidebar = create_side(device.services)
    for service in device.services:
        _hash = _get_hash(service)
        new_hashes.append(_hash)
        if _hash in old_hashes:
            logging.debug("Skipping %s serialization" % service.name)
            continue
        serialize_service(sidebar, device.name, service)
    _hash = _get_hash(device)
    new_hashes.append(_hash)
    if _hash not in old_hashes:
        serialize_device(sidebar, device)
    else:
        logging.debug("Skipping device serialization")
    _write_hashes(new_hashes)
