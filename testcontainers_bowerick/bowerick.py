# Copyright 2022, 2023 Ruediger Gad <r.c.g@gmx.de>
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

from aenum import Enum
import logging
import re
import stomp
import time
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_container_is_ready

logger = logging.getLogger(__name__)

SERVER_CERT_FILE='bowerick_testcontainers_server_certificate.pem'
CLIENT_CERT_FILE='bowerick_testcontainers_client_certificate.pem'
CLIENT_PRIV_KEY_FILE='bowerick_testcontainers_client_private_key.pem'

class Protocols(str, Enum):
    _init_ = 'value __doc__'
    TCP = 'tcp', 'Unencrypted OpenWire, the default protocol of ActiveMQ.'
    MQTT = 'mqtt', 'Unencrypted MQTT'
    WS = 'ws', 'Unencrypted STOMP via WebSockets'
    STOMP = 'stomp', "Unencrypted STOMP"
    SSL = 'ssl', 'Encrypted OpenWire'
    STOMP_SSL = 'stomp+ssl', 'Encrypted STOMP'
    MQTT_SSL = 'mqtt+ssl', 'Encrypted MQTT'
    WSS = 'wss', 'Encrypted STOMP via WebSockets'

class BowerickContainerState(Enum):
    WAITING = 0
    READY = 1
    TIMEOUT = 2

class BowerickContainer(DockerContainer):
    """
    Message-oriented Middleware (MoM) container using bowerick as MoM wrapper for the broker.
    MoM protocols supported by bowerick are: MQTT, STOMP, STOMP via WebSockets, and OpenWire.

    Example
    -------
    The example spins up a Bowerick instance and sends/receives data via STOMP producer/consumer.
    ::

        import stomp
        from testcontainers_bowerick.bowerick import BowerickContainer, Protocols
        import time

        class Listener(stomp.ConnectionListener):
            def on_message(self, frame):
                print(frame.body)

        with BowerickContainer() as container:
            conn = stomp.Connection([('127.0.0.1', container.get_port_for_protocol(Protocols.STOMP))])
            conn.connect(wait=True)
            conn.subscribe('/topic/foo', 1)
            conn.set_listener('listener', Listener())
            time.sleep(1)
            conn.send(body='bar', destination='/topic/foo')
            conn.disconnect()
    """

    def __init__(self, image="ruedigergad/bowerick:latest", mom_protocols=None, max_retries=30, **kwargs):
        super(BowerickContainer, self).__init__(image=image, **kwargs)
        logger.info('Creating bowerick container...')
        self.state = BowerickContainerState.WAITING
        
        if not mom_protocols:
            mom_protocols = {
                    Protocols.TCP: 1031,
                    Protocols.MQTT: 1701,
                    Protocols.WS: 1864,
                    Protocols.STOMP: 2000,
                    Protocols.SSL: 11031,
                    Protocols.STOMP_SSL: 11701,
                    Protocols.MQTT_SSL: 11864,
                    Protocols.WSS: 12000
                    }

        self.max_retries = max_retries
        self.mom_protocols = mom_protocols
        if not Protocols.STOMP in self.mom_protocols:
            self.mom_protocols[Protocols.STOMP] = 2000
        logger.info(f'Protocols: {self.mom_protocols}')
        self.with_exposed_ports(*self.mom_protocols.values())

        urls = [f'{k.value}://0.0.0.0:{v}' for k, v in self.mom_protocols.items()]
        urls_str = ' '.join(urls)
        logger.info(f'URLS: {urls_str}')
        self.with_env('URLS', urls_str)

    @wait_container_is_ready()
    def _check_is_ready(self):
        logger.debug('Checking is_ready...')
        
        if self.state is BowerickContainerState.TIMEOUT:
            raise Exception('Timed out while waiting for bowerick container to get ready.')
        
        return self.state is BowerickContainerState.READY

    def _wait_ready(self):
        logger.info('While waiting, some warning messages saying, e.g., "... could not connect ...", may show. This is usually normal.')
        ready = [False]
        retries = 0

        while not ready[-1] and retries < self.max_retries:
            try:
                logger.debug('Creating test connection. Note, this may fail a few times until the container is ready.')
                conn = stomp.Connection([('127.0.0.1', self.get_port_for_protocol(Protocols.STOMP))])
                conn.connect(wait=True)
                topic = '/topic/bowerick.testcontainers.is.ready'
                conn.subscribe(topic, 1)
                msg_body = 'wait_container_is_ready'
                class Listener(stomp.ConnectionListener):
                    def on_message(self, frame):
                        logger.debug('Received message while waiting: %s', msg_body)
                        if frame.body == msg_body:
                            logger.info('Received check message.')
                            ready.append(True)
                conn.set_listener('listener', Listener())
                logger.debug('Sending test message...')
                conn.send(body=msg_body, destination=topic)
                logger.debug('Waiting for test message to arrive...')
                time.sleep(5)
                logger.debug('Check iteration timed out...')
                conn.remove_listener('listener')
                conn.disconnect()
            except BaseException as e:
                logger.debug('Connection attempt failed with: %s, %s', type(e), str(e))
            time.sleep(1)
            retries += 1
        
        return ready[-1]

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

    def get_port_for_protocol(self, protocol: Protocols):
        if not protocol or not protocol in self.mom_protocols:
            raise RuntimeError(f'No matching protocol "{protocol}" defined for container. Available protocols are: {self.mom_protocols}')
        return super().get_exposed_port(self.mom_protocols[protocol])

    def start(self):
        logger.info('Starting bowerick container...')
        super().start()

        logger.info('Waiting for bowerick container to become ready. This may take some time.')
        is_ready = self._wait_ready()
        if is_ready:
            logger.info('bowerick is ready.')
            logger.info('Processing bowerick container cryptography files...')
            self._write_cryptography_files()
            self.state = BowerickContainerState.READY
        else:
            logger.error('Timed out while waiting for bowerick to get ready.')
            self.state = BowerickContainerState.TIMEOUT
        
        return self
