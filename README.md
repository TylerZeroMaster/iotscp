## Internet of Things Secure Control Protocol(IOTSCP)
***
### Project Vision
I started this project in 2017 with one goal. Provide a **simple, open, and secure** interface for creating and interacting with IoT devices. This interface should **limit control to a specific subset of network hosts.** More hosts can be added to the subset at any time **at the behest of the network administrator.** Unfortunately, I got a bit sidetracked for the last few years and never got around to sharing this project or making good on my future plans. Maybe one day I will: no promises.

Learning about an IOTSCP device--including specific details about how to control it--should be as easy as browsing to a web page.
***
### The state of things
This project is in early alpha. Features are still being added, stability is still being tested, and optimizations are pending.
***
### Who will use this project?
This project, in its current state, is intended to be used in DIY projects.
***
### Usage
#### Creating a device
See [this example](./examples/userdevice_tutorial.py) for more information about how the setup a device
#### First-time setup
Before you can connect a host to the device, you need a certificate. To make a certificate, start the device server with `get_cert` as the first argument. You can also, optionally, define the certificate size, `segments` and `segment length`, with the `--certsize` argument. Once the certificate has been generated, the next step is to copy it to the host. I recommend using some form of secure copy (rsync/scp) to copy the certificate to the host. The certificate should be ***two*** directories above sccertificate.py in a folder called "certificates"
#### Host setup
Hosts should use the `SCDevice` class in [scdevice.py](./iotscp/scdevice.py) as a base for creating and communicating with IOTSCP devices. Additionally, the `SCFinder` class can be used to discover devices on the network. When you subscribe to a device, event notification are sent to the host HTTP server as `NOTIFY` messages.

**Note:** If an IOTSCP device terminates a host's subscription, the host will be unaware. A solution to this is forthcoming: for now, you can either ignore the problem (it hasn't been a huge issue in tests) or try to cook up your own solution.
#### Other usage
For other usage questions, refer to `--help`
***
### Known issues
* No option for non-interactive execution
* Sometimes the UDP server will not receive discovery requests from the multicast group until a restart occurs.
* The HTTP server's stability/durability has not been tested thoroughly (Do not expose it online)
* Subscription requests to a device can silently fail in some cases.
* The serializer uses more memory than necessary
* `event_url` and `control_url` cannot contain characters outside the ascii range
