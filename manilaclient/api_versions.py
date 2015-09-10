# Copyright 2015 Chuck Fouts
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import manilaclient
from manilaclient.common import constants


def experimental_api(f):
    """Adds to HTTP Header to indicate this is an experimental API call."""
    def _decorator(*args, **kwargs):
        client = args[0]
        if isinstance(client, manilaclient.v1.client.Client):
            dh = client.client.default_headers
            dh[constants.EXPERIMENTAL_HTTP_HEADER] = 'true'
        f(*args, **kwargs)
    return _decorator