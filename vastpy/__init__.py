from urllib3.exceptions import InsecureRequestWarning
import urllib3
import http
import json

class RESTFailure(Exception):
    def __init__(self, method, url, fields, status, data):
        self.method = method
        self.url = url
        self.fields = fields
        self.status = status
        self.data = data

        super().__init__(f'response for {method} {url} with params={fields} failed with error {status} and message {data.decode("utf-8")}')

SUCCESS_CODES = {http.HTTPStatus.OK,
                 http.HTTPStatus.CREATED,
                 http.HTTPStatus.ACCEPTED,
                 http.HTTPStatus.NON_AUTHORITATIVE_INFORMATION,
                 http.HTTPStatus.NO_CONTENT,
                 http.HTTPStatus.RESET_CONTENT,
                 http.HTTPStatus.PARTIAL_CONTENT}

class VASTClient(object):
    def __init__(self, user=None, password=None, address=None, url='api', cert_file=None, cert_server_name=None, tenant=None, token=None, version=None):
        self._user = user
        self._password = password
        self._tenant = tenant
        self._token = token 
        self._address = address
        self._cert_file = cert_file
        self._cert_server_name = cert_server_name
        self._url = url
        self._version = version
        has_token = self._token is not None 
        has_userpass = (self._user is not None or self._password is not None)

        if not has_token and not has_userpass:
            raise ValueError("Must provide either username/password or token")
        if has_token and has_userpass:
            raise ValueError("Must provide exactly one of the following - username/password or token")
        if not self._address:
            raise ValueError("Must provide a VMS address")

    def __getattr__(self, part):
        return self[part]

    def __getitem__(self, part):
        version_path = f'/{self._version}' if self._version else ''
        return self.__class__(user=self._user,
                              password=self._password,
                              address=self._address,
                              cert_file=self._cert_file,
                              cert_server_name=self._cert_server_name,
                              url=f'{self._url}{version_path}/{part}',
                              tenant=self._tenant,
                              token=self._token)

    def __repr__(self):
        return f'VASTClient(address="{self._address}", url="{self._url}")'

    def request(self, method, fields=None, data=None):
        if self._cert_file:
            pm = urllib3.PoolManager(ca_certs=self._cert_file, server_hostname=self._cert_server_name)
        else:
            pm = urllib3.PoolManager(cert_reqs='CERT_NONE')
            urllib3.disable_warnings(category=InsecureRequestWarning)
        if self._token:
            headers = {'authorization': f"'Api-Token {self._token}"}
        else:
            headers = urllib3.make_headers(basic_auth=self._user + ':' + self._password)
        if self._tenant:
            headers['X-Tenant-Name'] = self._tenant
        if data:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data).encode('utf-8')
        if fields:
            result = []
            for k, v in fields.items():
                if isinstance(v, list):
                    result.extend((k, i) for i in v)
                else:
                    result.append((k, v))
            fields = result
        version_path = f'/{self._version}' if self._version else ''
        r = pm.request(method, f'https://{self._address}/{self._url}{version_path}/', headers=headers, fields=fields, body=data)
        if r.status not in SUCCESS_CODES:
            raise RESTFailure(method, self._url, fields, r.status, r.data)
        data = r.data
        if 'application/json' in r.headers.get('Content-Type', '') and data:
            return json.loads(data.decode('utf-8'))
        return data

    def get(self, **params):
        return self.request('GET', fields=params)
    def post(self, **params):
        return self.request('POST', data=params)
    def put(self, **params):
        return self.request('PUT', data=params)
    def patch(self, **params):
        return self.request('PATCH', data=params)
    def options(self, **params):
        return self.request('OPTIONS', fields=params)
    def delete(self, **params):
        return self.request('DELETE', data=params)
