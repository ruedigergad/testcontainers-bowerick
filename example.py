#!/usr/bin/env python3

# Copyright 2022 Ruediger Gad <r.c.g@gmx.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import stomp
from testcontainers_bowerick.bowerick import BowerickContainer
import time

class Listener(stomp.ConnectionListener):
    def on_message(self, frame):
        print(frame.body)

with BowerickContainer() as container:
    conn = stomp.Connection([('127.0.0.1', container.get_port_for_protocol('stomp'))])
    conn.connect(wait=True)
    conn.subscribe('/topic/foo', 1)
    conn.set_listener('listener', Listener())
    time.sleep(1)
    conn.send(body='bar', destination='/topic/foo')
    conn.disconnect()
