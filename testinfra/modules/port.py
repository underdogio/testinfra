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

    def _parse_address_port(self, local_address):
        raise NotImplementedError

    def _get_connection_information(self):
        """Helper method to search for data about the expected <address>:<port> connection"""
        results = self.run_test(self._netstat_command())
        lines = results.stdout.split("\n")

        for line in lines:
            parts = re.split("\s+", line.strip())
            # Skip any lines which do not have enough parts (e.g. header or footer lines)
            if len(parts) != 6:
                continue

            # Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)
            proto, _, _, local_address, foreign_address, state = parts
            address, port = self._parse_address_port(local_address)

            if address == self.address and port == self.port:
                self.address = address
                self.port = port
                self.protocol = proto
                self.state = state
                break

    @property
    def is_tcp(self):
        """Test if port is using tcp

        >>> Port("0.0.0.0", 22).is_tcp
        True
        >>> Port("127.0.0.1", 53).is_tcp
        False

        """
        return self.protocol and self.protocol.startswith("tcp")

    @property
    def is_udp(self):
        """Test if port is using udp

        >>> Port("0.0.0.0", 53).is_udp
        True
        >>> Port("0.0.0.0", 22).is_tcp
        False

        """
        return self.protocol and self.protocol.startswith("tcp")

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
        elif SystemInfo.type.endswith("bsd") or SystemInfo.type == "darwin":
            return BSDPort(_backend, None, None)
        else:
            raise NotImplementedError


class GNUPort(Port):
    def _netstat_command(self):
        return "netstat -tunl"

    def _parse_address_port(self, local_address):
        if local_address.startswith("*:"):
            local_address = "0.0.0.0" + local_address[1:]
        address, _, port = local_address.partition(":")
        return address, int(port)

class BSDPort(Port):
    def _netstat_command(self):
        return "netstat -an -f inet"

    def _parse_address_port(self, local_address):
        if local_address.startswith("."):
            local_address = "0.0.0.0" + local_address[1:]

        address, _, port = local_address.rpartition(".")
        return address, int(port)
