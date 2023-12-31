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

import json
import logging
import ssl
import stomp
import testcontainers_bowerick.bowerick as bowerick
from threading import Semaphore
import time
import unittest

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

class BowerickTestcontainerTests(unittest.TestCase):

    # Bowerick includes a message generator that generates messages in tregular intervals as test data.
    # This test aims on receiving one such message.
    def test_stomp_consumer(self):
        semaphore = Semaphore(0)
        data = []

        class Listener(stomp.ConnectionListener):
            def on_message(self, frame):
                data.append(json.loads(frame.body))
                semaphore.release()

        with bowerick.BowerickContainer() as container:
            address = [('127.0.0.1', container.get_port_for_protocol('stomp'))]
            logger.info(f'Connecting to: {address}')
            conn = stomp.Connection(address)
            conn.connect(wait=True)
            conn.subscribe('/topic/bowerick.message.generator', 1)
            conn.set_listener('listener', Listener())

            semaphore.acquire()

            conn.remove_listener('listener')
            conn.disconnect()

        self.assertTrue('x' in data[0][0])
        self.assertTrue('y' in data[0][0])
        self.assertTrue('z' in data[0][0])

    def test_stomp_producer_consumer(self):
        semaphore = Semaphore(0)
        data = []
        msg = 'Temba, his arms wide.'
        topic = '/topic/at.tanagra'

        class Listener(stomp.ConnectionListener):
            def on_message(self, frame):
                data.append(frame.body)
                semaphore.release()

        with bowerick.BowerickContainer() as container:
            address = [('127.0.0.1', container.get_port_for_protocol('stomp'))]
            logger.info(f'Connecting to: {address}')
            conn = stomp.Connection(address)
            conn.connect(wait=True)
            conn.subscribe(topic, 1)
            conn.set_listener('listener', Listener())

            time.sleep(1)
            conn.send(body=msg, destination=topic)

            semaphore.acquire()

            conn.remove_listener('listener')
            conn.disconnect()

        self.assertTrue(msg, data[0])

    def test_ssl_stomp_producer_consumer(self):
        semaphore = Semaphore(0)
        data = []
        msg = 'Temba, his arms wide.'
        topic = '/topic/at.tanagra'

        class Listener(stomp.ConnectionListener):
            def on_message(self, frame):
                data.append(frame.body)
                semaphore.release()

        with bowerick.BowerickContainer() as container:
            address = [('127.0.0.1', container.get_port_for_protocol('stomp+ssl'))]
            logger.info(f'Connecting to: {address}')
            conn = stomp.Connection(address)
            stomp.transport.DEFAULT_SSL_VERSION=ssl.PROTOCOL_TLS_CLIENT
            conn.set_ssl(
                    address,
                    key_file=bowerick.CLIENT_PRIV_KEY_FILE,
                    cert_file=bowerick.CLIENT_CERT_FILE,
                    ca_certs=bowerick.SERVER_CERT_FILE,
                    ssl_version=ssl.PROTOCOL_TLS_CLIENT
                    )
            conn.connect(wait=True)
            conn.subscribe(topic, 1)
            conn.set_listener('listener', Listener())

            time.sleep(1)
            conn.send(body=msg, destination=topic)

            semaphore.acquire()

            conn.remove_listener('listener')
            conn.disconnect()

        self.assertTrue(msg, data[0])
