# -*- coding: utf-8 -*-
# pylint: disable=too-many-arguments,redefined-outer-name
import copy

import pytest
from gevent import Greenlet

from raiden.app import App
from raiden.api.rest import RestAPI, APIServer
from raiden.raiden_service import RaidenService
from raiden.network.discovery import Discovery
from raiden.tests.utils.apitestcontext import ApiTestContext


# TODO: Figure out why this fixture can't work as session scoped
#       What happens is that after one test is done, in the next one
#       the server is no longer running even though the teardown has not
#       been invoked.
@pytest.fixture
def api_backend(rest_api_port_number):
    # Initializing it without raiden_service.api here since that is a
    # function scope fixture. We will inject it to rest_api object later
    rest_api = RestAPI(None)
    api_server = APIServer(rest_api)
    api_server.flask_app.config['SERVER_NAME'] = 'localhost:{}'.format(rest_api_port_number)

    # TODO: Find out why tests fail with debug=True
    server = Greenlet.spawn(
        api_server.run,
        rest_api_port_number,
        debug=False,
        use_evalex=False,
    )

    yield api_server, rest_api

    server.kill(block=True, timeout=10)


@pytest.fixture
def api_raiden_service(
        monkeypatch,
        api_backend,
        api_test_context,
        blockchain_services,
        transport_class,
        max_unresponsive_time,
        send_ping_time,
        reveal_timeout,
        raiden_udp_ports):

    blockchain = blockchain_services[0]
    config = copy.deepcopy(App.default_config)

    config['port'] = raiden_udp_ports[0]
    config['host'] = '127.0.0.1'
    config['privatekey_hex'] = blockchain.private_key.encode('hex')
    config['send_ping_time'] = send_ping_time
    config['max_unresponsive_time'] = max_unresponsive_time
    config['reveal_timeout'] = reveal_timeout
    raiden_service = RaidenService(
        blockchain,
        blockchain.private_key,
        transport_class,
        Discovery(),
        config
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_channel_list',
        api_test_context.query_channels
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_tokens_list',
        api_test_context.query_tokens
    )
    monkeypatch.setattr(
        raiden_service.api,
        'open',
        api_test_context.open_channel
    )
    monkeypatch.setattr(
        raiden_service.api,
        'deposit',
        api_test_context.deposit
    )
    monkeypatch.setattr(
        raiden_service.api,
        'close',
        api_test_context.close
    )
    monkeypatch.setattr(
        raiden_service.api,
        'settle',
        api_test_context.settle
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_channel',
        api_test_context.get_channel
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_network_events',
        api_test_context.get_network_events
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_token_network_events',
        api_test_context.get_token_network_events
    )
    monkeypatch.setattr(
        raiden_service.api,
        'get_channel_events',
        api_test_context.get_channel_events
    )
    monkeypatch.setattr(
        raiden_service.api,
        'transfer',
        api_test_context.transfer
    )
    monkeypatch.setattr(
        raiden_service.api,
        'token_swap',
        api_test_context.token_swap
    )
    monkeypatch.setattr(
        raiden_service.api,
        'expect_token_swap',
        api_test_context.expect_token_swap
    )

    # also make sure that the test server's raiden_api uses this mock
    # raiden service
    _, raiden_api = api_backend
    monkeypatch.setattr(
        raiden_api,
        'raiden_api',
        raiden_service.api
    )
    return raiden_service


@pytest.fixture
def api_test_context(reveal_timeout):
    return ApiTestContext(reveal_timeout)
