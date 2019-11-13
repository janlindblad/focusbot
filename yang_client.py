#   YANG Client
#   Copyright (C) 2019 Jan Lindblad
# 
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import requests
import json

class restconf_client:
    def __init__(self, host, port, user, password, proto="https"):
        self.proto = proto
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def _get_root_url(self):
        # FIXME:
        # GET /.well-known/host-meta HTTP/1.1
        # Accept: application/xrd+xml
        return f"{self.proto}://{self.host}:{self.port}/restconf/data"

    def _send_rpc(self, path, params={}, content_type=None, accept=None, headers={}, data={}):
        if content_type: 
            headers = {**headers, "Content-Type":content_type}
        if accept: 
            headers = {**headers, "Accept":accept}
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/yang-data+json"
        if "Accept" not in headers:
            headers["Accept"] = "application/yang-data+json"

        print(f"Restconf RPC to url={self._get_root_url() + path}, params={params}, headers={headers}, data={data}, auth={self.user}:{len(self.password)}")

        #return requests.post(self._get_root_url() + path,
        #    verify=False,
        #    data=data,
        #    auth=(self.user, self.password))
        return requests.post(self._get_root_url() + path,
            verify=False,
            params=params,
            headers=headers,
            data=json.dumps(data),
            auth=(self.user, self.password))

    def action(self, path, inputData):
        result = self._send_rpc(path, {}, None, None, {}, data=inputData)
        return result
