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

import logging
import re
import stomp
import time
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_container_is_ready

SERVER_CERT_FILE='bowerick_testcontainers_server_certificate.pem'
CLIENT_CERT_FILE='bowerick_testcontainers_client_certificate.pem'
CLIENT_PRIV_KEY_FILE='bowerick_testcontainers_client_private_key.pem'

class BowerickContainer(DockerContainer):
    """
    Message-oriented Middleware (MoM) container using bowerick as MoM wrapper for the broker.
    MoM protocols supported by bowerick are: MQTT, STOMP, STOMP via WebSockets, and OpenWire.

    Example
    -------
    The example spins up a Bowerick instance and sends/receives data via STOMP producer/consumer.
    ::

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
    """

    def __init__(self, image="ruedigergad/bowerick:latest", mom_protocols=None):
        super(BowerickContainer, self).__init__(image=image)

        if not mom_protocols:
            mom_protocols = {
                    'tcp': 1031,
                    'mqtt': 1701,
                    'ws': 1864,
                    'stomp': 2000,
                    'ssl': 11031,
                    'stomp+ssl': 11701,
                    'mqtt+ssl': 11864,
                    'wss': 12000
                    }

        self.mom_protocols = mom_protocols
        if not 'stomp' in self.mom_protocols:
            self.mom_protocols['stomp'] = 2000
        logging.info(f'Protocols: {self.mom_protocols}')
        self.with_exposed_ports(*self.mom_protocols.values())

        urls = [f'{k}://0.0.0.0:{v}' for k, v in self.mom_protocols.items()]
        urls_str = ' '.join(urls)
        logging.info(f'URLS: {urls_str}')
        self.with_env('URLS', urls_str)

    def _wait_ready(self):
        logging.info('Waiting for bowerick to become ready.')
        ready = [False]
        while not ready[-1]:
            try:
                conn = stomp.Connection([('127.0.0.1', self.get_port_for_protocol('stomp'))])
                conn.connect(wait=True)
                topic = '/topic/bowerick.testcontainers.is.ready'
                conn.subscribe(topic, 1)
                msg_body = 'wait_container_is_ready'
                class Listener(stomp.ConnectionListener):
                    def on_message(self, frame):
                        if frame.body == msg_body:
                            ready.append(True)
                conn.set_listener('listener', Listener())
                conn.send(body=msg_body, destination=topic)
                time.sleep(1)
                conn.remove_listener('listener')
                conn.disconnect()
            except:
                pass
            time.sleep(1)
        logging.info('Bowerick is ready.')

    def _write_cryptography_files(self):
        log = super().get_wrapped_container().logs().decode()

        certificates = re.findall(r'-----BEGIN CERTIFICATE-----[\S\r\n]*-----END CERTIFICATE-----', log, re.MULTILINE)
        private_keys = re.findall(r'-----BEGIN PRIVATE KEY-----[\S\r\n]*-----END PRIVATE KEY-----', log, re.MULTILINE)

        with open(SERVER_CERT_FILE, 'w') as f:
            f.write(certificates[0])
        with open(CLIENT_CERT_FILE, 'w') as f:
            f.write(certificates[1])
        with open(CLIENT_PRIV_KEY_FILE, 'w') as f:
            f.write(private_keys[0])

    def get_port_for_protocol(self, protocol):
        if not protocol or not protocol in self.mom_protocols:
            raise RuntimeError(f'No matching protocol "{protocol}" defined for container. Available protocols are: {self.mom_protocols}')
        return super().get_exposed_port(self.mom_protocols[protocol])

    def start(self):
        super().start()
        self._wait_ready()
        self._write_cryptography_files()
        return self

