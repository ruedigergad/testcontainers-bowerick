# Overview

[![PyPI version](https://badge.fury.io/py/testcontainers-bowerick.svg)](https://badge.fury.io/py/testcontainers-bowerick)
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/ruedigergad/testcontainers-bowerick/tree/master.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/ruedigergad/testcontainers-bowerick/tree/master)
[![Coverage Status](https://coveralls.io/repos/github/ruedigergad/testcontainers-bowerick/badge.svg?branch=master)](https://coveralls.io/github/ruedigergad/testcontainers-bowerick?branch=master)

This testcontainer provides multiple Message-oriented Middleware (MoM) protocols:

- OpenWire (ActiveMQ)
- MQTT
- STOMP
- STOMP via WebSockets

It support encrypted and unencrypted connections.

# Background

This testcontainer uses a container image of bowerick, which is a wrapper around ActiveMQ and other libraries.
bowerick is also available as Open Source Software: <https://github.com/ruedigergad/bowerick>

# Documentation

## Example

The example below shows how testcontainers-bowerick can be used with STOMP.
Note, this uses "stomp.py==8.*".

```
import stomp
from testcontainers_bowerick.bowerick import BowerickContainer, Protocols
import time

class Listener(stomp.ConnectionListener):
    def on_message(self, frame):
        print('Received message body:', frame.body)

with BowerickContainer() as container:
    conn = stomp.Connection([('127.0.0.1', container.get_port_for_protocol(Protocols.STOMP))])
    conn.connect(wait=True)
    conn.subscribe('/topic/foo', 1)
    conn.set_listener('listener', Listener())
    time.sleep(1)
    conn.send(body='bar', destination='/topic/foo')
    time.sleep(1)
    conn.disconnect()
```

