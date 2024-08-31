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

        super().__init__(f'Response for request {method} {url} with {fields} failed with error {status} and message {data}')

SUCCESS_CODES = {http.HTTPStatus.OK,
                 http.HTTPStatus.CREATED,
                 http.HTTPStatus.ACCEPTED,
                 http.HTTPStatus.NON_AUTHORITATIVE_INFORMATION,
                 http.HTTPStatus.NO_CONTENT,
                 http.HTTPStatus.RESET_CONTENT,
                 http.HTTPStatus.PARTIAL_CONTENT}

class VASTClient(object):
    def __init__(self, user, password, address, url='api', cert_file=None, cert_server_name=None):
        self._user = user
        self._password = password
        self._address = address
        self._cert_file = cert_file
        self._cert_server_name = cert_server_name
        self._url = url

    def __getattr__(self, part):
        return self[part]

    def __getitem__(self, part):
        return self.__class__(user=self._user,
                              password=self._password,
                              address=self._address,
                              cert_file=self._cert_file,
                              cert_server_name=self._cert_server_name,
                              url=f'{self._url}/{part}')

    def __repr__(self):
        return f'VASTClient(address="{self._address}", url="{self._url}")'

    def request(self, method, fields=None, data=None):
        if self._cert_file:
            pm = urllib3.PoolManager(ca_certs=self._cert_file, server_hostname=self._cert_server_name)
        else:
            pm = urllib3.PoolManager(cert_reqs='CERT_NONE')
            urllib3.disable_warnings(category=InsecureRequestWarning)
        headers = urllib3.make_headers(basic_auth=self._user + ':' + self._password)
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
        r = pm.request(method, f'https://{self._address}/{self._url}/', headers=headers, fields=fields, body=data)
        if r.status not in SUCCESS_CODES:
            raise RESTFailure(method, self._url, fields, r.status, r.data)
        data = r.data
        if data:
            return json.loads(data.decode('utf-8'))

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
