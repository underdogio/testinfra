# -*- coding: utf8 -*-
# Copyright © 2015 Philippe Pepiot
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

from __future__ import unicode_literals
import re

from testinfra.modules.base import Module


class Port(Module):
    """Test various active port attributes"""

    def __init__(self, _backend, address, port):
        self.address = address
        self.port = port
        self.protocol = None
        self.state = None
        super(Port, self).__init__(_backend)

    def __call__(self, address, port):
        instance = self.__class__(self._backend, address, port)
        instance._get_connection_information()
        return instance

    def _netstat_command(self):
        raise NotImplementedError

    def _get_connection_information(self):
        """Helper method to search for data about the expected <address>:<port> connection"""
        results = self.run_test(self._netstat_command())
        expected_address = "%s:%s" % (self.address, self.port)
        for line in results.stdout:
            # Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)
            proto, _, _, local_address, foreign_address, state = re.split("\s+", results.trim("\n"))
            if local_address.startswith("*:"):
                local_address = "0.0.0.0" + local_address[1:]

            if local_address == expected_address:
                address, port = local_address.split(":")
                self.address = address
                self.port = port
                self.protocol = proto
                self.state = state
                break

    @property
    def is_listening(self):
        """Test if port is listening

        >>> Port("0.0.0.0", 22).is_listening
        True
        >>> Port("127.0.0.1", 12345).is_listening
        False

        """
        return self.state == 'LISTEN'

    def __repr__(self):
        return "<port %s:%s>" % (self.address, self.port)

    @classmethod
    def get_module(cls, _backend):
        SystemInfo = _backend.get_module("SystemInfo")
        if SystemInfo.type == "linux":
            return GNUPort(_backend, None, None)
        elif SystemInfo.type.endswith("bsd"):
            return BSDPort(_backend, None, None)
        else:
            raise NotImplementedError


class GNUPort(Port):
    def _netstat_command(self):
        return "netstat -tunl"


class BSDPort(Port):
    def _netstat_command(self):
        return "netstat -an -f inet"
