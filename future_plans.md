## Plans for the future

### Immediate future
* Improve documentation
* Add a way to shutdown gracefully when running as a daemon.
* Make certificate key offset procedurally generated, thus eliminating the need for it to  be communicated
* Add support for pushing updates to devices.
* Add tests (Bad habits die hard)
* Externalize `serializer` templates so that templates may be customized
* Continue optimizing everything.
* Finish implementing query support in the discovery protocol.

### Potential changes/improvements
#### Remove encryption in favor of a token system
* Tokens used to prevent tampering and prove identity
* Tokens based on same keygen function
* Add the request body's checksum to the keygen to prevent tampering
* Advantages:
    - Less computationally intensive
    - Less error-prone
    - Less likely to expose shared secret
* Disadvantages:
    - Communications made less private
#### Split the program into several smaller programs
* Advantages:
    - Easier to manage individual parts
    - Improved performance
* Disadvantages:
    - Larger memory footprint
    - More complex launch/shutdown procedure
#### Add a uuid field to the discovery protocol
* Do not respond to discovery requests that lack a valid uuid
* Advantages:
    - Prevent message amplification used in DDOS attacks by making it less convenient
* Disadvantages:
    - Additional complexity
    - Someone could obtain a valid uuid by eavesdropping on network traffic, nullifying this defense
#### Make the service model more host-centric
* Allow the device service model, as defined in `userdevice.py` to be reused for programming hosts
* Advantages:
    - Less work involved with setting up a host
* Disadvantages:
    - Makes the distinction between *device* and *host* even less clear

### Long-term goals
* Make first-time setup easier by somehow eliminating the need for certificates.
* Extend language support for the API (port it to Rust, Java, etc.)
* Extend human language support (localize for German, French, etc.)
