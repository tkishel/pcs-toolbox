""" Requests and Output """

import json
import time

import requests

class PrismaCloudAPIPCCSMixin():
    """ Requests and Output """

    # pylint: disable=too-many-arguments,too-many-branches,too-many-locals,too-many-statements
    def execute_code_security(self, action, endpoint, query_params=None, body_params=None, request_headers=None, force=False, paginated=False):
        self.suppress_warnings_when_verify_false()
        if not self.token:
            self.login()
        if int(time.time() - self.token_timer) > self.token_limit:
            self.extend_login()
        if not request_headers:
            request_headers = {'Content-Type': 'application/json'}
        if body_params:
            body_params_json = json.dumps(body_params)
        else:
            body_params_json = None
        # Endpoints that return large numbers of results use a 'hasNext' key.
        # Pagination is via query parameters for both GET and POST, and appears to be specific to "List File Errors - POST".
        offset = 0
        limit = 50
        more = False
        results = []
        while offset == 0 or more is True:
            if int(time.time() - self.token_timer) > self.token_limit:
                self.extend_login()
            if paginated:
                url = 'https://%s/%s?limit=%s&offset=%s' % (self.api, endpoint, limit, offset)
            else:
                url = 'https://%s/%s' % (self.api, endpoint)
            if self.token:
                request_headers['authorization'] = self.token
            self.debug_print('API URL: %s' % url)
            self.debug_print('API Headers: %s' % request_headers)
            self.debug_print('API Query Params: %s' % query_params)
            self.debug_print('API Body Params: %s' % body_params_json)
            api_response = requests.request(action, url, headers=request_headers, params=query_params, data=body_params_json, verify=self.verify, timeout=self.timeout)
            self.debug_print('API Response Status Code: %s' % api_response.status_code)
            self.debug_print('API Response Headers: (%s)' % api_response.headers)
            if api_response.status_code in self.retry_status_codes:
                for exponential_wait in self.retry_waits:
                    time.sleep(exponential_wait)
                    api_response = requests.request(action, url, headers=request_headers, params=query_params, data=body_params_json, verify=self.verify, timeout=self.timeout)
                    if api_response.ok:
                        break # retry loop
            if api_response.ok:
                if not api_response.content:
                    return None
                if api_response.headers.get('Content-Type') == 'application/x-gzip':
                    return api_response.content
                if api_response.headers.get('Content-Type') == 'text/csv':
                    return api_response.content.decode('utf-8')
                try:
                    result = json.loads(api_response.content)
                    #if result is None:
                    #    self.logger.error('JSON returned None, API: (%s) with query params: (%s) and body params: (%s) parsing response: (%s)' % (url, query_params, body_params, api_response.content))
                    #    if force:
                    #        return results # or continue
                    #    self.error_and_exit(api_response.status_code, 'JSON returned None, API: (%s) with query params: (%s) and body params: (%s) parsing response: (%s)' % (url, query_params, body_params, api_response.content))
                except ValueError:
                    self.logger.error('JSON raised ValueError, API: (%s) with query params: (%s) and body params: (%s) parsing response: (%s)' % (url, query_params, body_params, api_response.content))
                    if force:
                        return results # or continue
                    self.error_and_exit(api_response.status_code, 'JSON raised ValueError, API: (%s) with query params: (%s) and body params: (%s) parsing response: (%s)' % (url, query_params, body_params, api_response.content))
                if paginated:
                    results.extend(result['data'])
                    if 'hasNext' in result:
                        self.debug_print('Retrieving Next Page of Results')
                        offset += limit
                        more = result['hasNext']
                    else:
                        return results
                else:
                    return result
            else:
                self.logger.error('API: (%s) responded with a status of: (%s), with query: (%s) and body params: (%s)' % (url, api_response.status_code, query_params, body_params))
                if force:
                    return results
                self.error_and_exit(api_response.status_code, 'API: (%s) with query params: (%s) and body params: (%s) responded with an error and this response:\n%s' % (url, query_params, body_params, api_response.text))
        return results

    # Exit handler (Error).

    @classmethod
    def error_and_exit(cls, error_code, error_message='', system_message=''):
        raise SystemExit('\n\nStatus Code: %s\n%s\n%s\n' % (error_code, error_message, system_message))
