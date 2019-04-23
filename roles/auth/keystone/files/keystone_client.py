#!/usr/bin/env python

import os.path
import requests
import sys
import json

from argparse import ArgumentParser
from datetime import datetime

# URL Parse
try:
    # Python 2.x
    from urlparse import urlparse, urlunparse, urljoin
except ImportError:
    # Python 3.x
    from urllib.parse import urlparse, urlunparse, urljoin


__author__ = "Lisa Zangrando"
__email__ = "lisa.zangrando[AT]pd.infn.it"
__copyright__ = """Copyright (c) 2019 INFN
All Rights Reserved

Licensed under the Apache License, Version 2.0;
you may not use this file except in compliance with the
License. You may obtain a copy of the License at:

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.
See the License for the specific language governing
permissions and limitations under the License."""


class Token(object):

    def __init__(self, token, data):
        self.id = token

        data = data["token"]
        self.roles = data["roles"]
        self.catalog = data["catalog"]
        self.issued_at = datetime.strptime(data["issued_at"],
                                           "%Y-%m-%dT%H:%M:%S.%fZ")
        self.expires_at = datetime.strptime(data["expires_at"],
                                            "%Y-%m-%dT%H:%M:%S.%fZ")
        self.project = data["project"]
        self.user = data["user"]

        if "extras" in data:
            self.extras = data["extras"]

    def getCatalog(self, service_name=None, interface="public"):
        if service_name:
            for service in self.catalog:
                if service["name"] == service_name:
                    for endpoint in service["endpoints"]:
                        if endpoint["interface"] == interface:
                            return endpoint
            return None
        else:
            return self.catalog

    def getExpiration(self):
        return self.expires_at

    def getId(self):
        return self.id

    def getExtras(self):
        return self.extras

    def getProject(self):
        return self.project

    def getRoles(self):
        return self.roles

    def getUser(self):
        return self.user

    def isAdmin(self):
        if not self.roles:
            return False

        for role in self.roles:
            if role["name"] == "admin":
                return True

        return False

    def issuedAt(self):
        return self.issued_at

    def isExpired(self):
        return self.getExpiration() < datetime.utcnow()

    def save(self, filename):
        # save to file
        with open(filename, 'w') as f:
            token = {}
            token["catalog"] = self.catalog
            token["extras"] = self.extras
            token["user"] = self.user
            token["project"] = self.project
            token["roles"] = self.roles
            token["roles"] = self.roles
            token["issued_at"] = self.issued_at.isoformat()
            token["expires_at"] = self.expires_at.isoformat()

            data = {"id": self.id, "token": token}

            json.dump(data, f)

    @classmethod
    def load(cls, filename):
        if not os.path.isfile(".auth_token"):
            return None

        # load from file:
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
                return Token(data["id"], data)
            # if the file is empty the ValueError will be thrown
            except ValueError as ex:
                raise ex

    def isotime(self, at=None, subsecond=False):
        """Stringify time in ISO 8601 format."""
        if not at:
            at = datetime.utcnow()

        if not subsecond:
            st = at.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            st = at.strftime('%Y-%m-%dT%H:%M:%S.%f')

        if at.tzinfo:
            tz = at.tzinfo.tzname(None)
        else:
            tz = 'UTC'

        st += ('Z' if tz == 'UTC' else tz)
        return st

    """The trustor or grantor of a trust is the person who creates the trust.
    The trustor is the one who contributes property to the trust.
    The trustee is the person who manages the trust, and is usually appointed
    by the trustor. The trustor is also often the trustee in living trusts.
    """
    def trust(self, trustee_user, expires_at=None,
              project_id=None, roles=None, impersonation=True):
        if self.isExpired():
            raise Exception("token expired!")

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": "python-novaclient",
                   "X-Auth-Token": self.getId()}

        if roles is None:
            roles = self.getRoles()

        if project_id is None:
            project_id = self.getProject().get("id")

        data = {}
        data["trust"] = {"impersonation": impersonation,
                         "project_id": project_id,
                         "roles": roles,
                         "trustee_user_id": trustee_user,
                         "trustor_user_id": self.getUser().get("id")}

        if expires_at is not None:
            data["trust"]["expires_at"] = self.isotime(expires_at, True)

        endpoint = self.getCatalog(service_name="keystone")

        if not endpoint:
            raise Exception("keystone endpoint not found!")

        if "v2.0" in endpoint["url"]:
            endpoint["url"] = endpoint["url"].replace("v2.0", "v3")

        response = requests.post(url=endpoint["url"] + "/OS-TRUST/trusts",
                                 headers=headers,
                                 data=json.dumps(data))

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        if not response.text:
            raise Exception("trust token failed!")

        return Trust(response.json())


def get_access_token(checkin_url, client_id, client_secret, refresh_token):
    refresh_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': 'openid email profile',
    }

    r = requests.post(urljoin(checkin_url, "oidc/token"),
                      auth=(client_id, client_secret), data=refresh_data)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()
    return r.json()['access_token']


def get_keystone_url(os_auth_url, path):
    url = urlparse(os_auth_url)
    prefix = url.path.rstrip('/')

    if prefix.endswith('v2.0') or prefix.endswith('v3'):
        prefix = os.path.dirname(prefix)

    path = os.path.join(prefix, path)
    return urlunparse((url[0], url[1], path, url[3], url[4], url[5]))


def get_unscoped_token(os_auth_url, access_token=None, voms_proxy=None):
    if access_token:
        url = get_keystone_url(
            os_auth_url,
            "/v3/OS-FEDERATION/identity_providers/egi.eu/protocols/openid/auth")

        r = requests.post(url,
                          headers={'Authorization': 'Bearer %s' % access_token})
    elif voms_proxy:
        url = get_keystone_url(os_auth_url, "/v3/auth/tokens")
        data = {}
        data["auth"] = {
            'identity': {
                'methods': ['mapped'],
                'mapped': {
                    'voms': True,
                    'identity_provider': 'egi.eu',
                    'protocol': 'mapped'
                }
            }
        }

        r = requests.post(url,
                          headers={'content-type': 'application/json'},
                          data=json.dumps(data),
                          cert=voms_proxy)
                          #verify=os_ca_cert)
    else:
        raise Exception("access_token or voms_proxy not defined!")

    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    return r.headers['X-Subject-Token']


def get_unscoped_token3(os_auth_url, voms_proxy, os_ca_cert=None):
    url = get_keystone_url(os_auth_url, "/v3/auth/tokens")
    data = {}
    data["auth"] = {
        'identity': {
            'methods': ['mapped'],
            'mapped': {
                'voms': True,
                'identity_provider': 'egi.eu',
                'protocol': 'mapped'
            }
        }
    }

    r = requests.post(url,
                      headers={'content-type': 'application/json'},
                      data=json.dumps(data),
                      cert=voms_proxy)
                      #verify=os_ca_cert)

    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    return r.headers['X-Subject-Token']


def get_scoped_token2(os_auth_url, unscoped_token, os_project_id=None, os_project_name=None):
    url = get_keystone_url(os_auth_url, "/v3/auth/tokens")
    token_body = {}
    token_body["auth"] = {
        "identity": {
            "methods": ["token"],
            "token": {"id": unscoped_token}
        }
    }

    if os_project_id:
        token_body["scope"] = {"project": {"id": os_project_id}}
    elif os_project_name:
        token_body["scope"] = {"project": {"name": os_project_name}}

    r = requests.post(url, headers={'content-type': 'application/json'},
                      data=json.dumps(token_body))
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    return r.headers['X-Subject-Token']


def get_scoped_token(os_auth_url,
                     os_auth_type="password",
                     os_access_token=None,
                     os_username=None,
                     os_password=None,
                     os_user_domain_id=None,
                     os_user_domain_name="default",
                     os_project_id=None,
                     os_project_name=None,
                     os_project_domain_id=None,
                     os_project_domain_name="default",
                     os_ca_cert=None,
                     timeout=None,
                     unscoped_token=None):
    url = get_keystone_url(os_auth_url, "/v3/auth/tokens")

    project_domain = {}
    if os_project_domain_id is not None:
        project_domain["id"] = os_project_domain_id
    else:
        project_domain["name"] = os_project_domain_name

    if os_auth_type == "password":
        user_domain = {}
        if os_user_domain_id is not None:
            user_domain["id"] = os_user_domain_id
        else:
            user_domain["name"] = os_user_domain_name

        identity = {"methods": ["password"],
                    "password": {"user": {"name": os_username,
                                          "domain": user_domain,
                                          "password": os_password}}}

        data = {"auth": {}}
        data["auth"]["identity"] = identity

        if os_project_name:
            data["auth"]["scope"] = {"project": {"name": os_project_name,
                                                 "domain": project_domain}}
        elif os_project_id:
            data["auth"]["scope"] = {"project": {"id": os_project_id,
                                                 "domain": project_domain}}
    elif os_auth_type == "token":
        data = {}
        data["auth"] = {
            "identity": {
                "methods": ["token"],
                "token": {"id": unscoped_token}
            }
        }

        if os_project_id:
            data["auth"]["scope"] = {"project": {"id": os_project_id,
                                                "domain": project_domain}}
        elif os_project_name:
            data["auth"]["scope"] = {"project": {"name": os_project_name,
                                                 "domain": project_domain}}

    response = requests.post(url=url,
                             headers={'content-type': 'application/json'},
                             data=json.dumps(data),
                             timeout=timeout)
                             #verify=os_ca_cert)

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    if not response.text:
        raise Exception("authentication failed!")

    # print(response.__dict__)

    token_subject = response.headers["X-Subject-Token"]
    token_data = response.json()

    return Token(token_subject, token_data)


def main():
    try:
        parser = ArgumentParser(prog="keystone_client",
                                epilog="Command-line interface to the"
                                       " OpenStack Synergy API.")

        # Global arguments
        parser.add_argument("--version", action="version", version="v1.0")

        parser.add_argument("--debug",
                            default=False,
                            action="store_true",
                            help="print debugging output")

        parser.add_argument("--os-username",
                            metavar="<auth-user-name>",
                            default=os.environ.get("OS_USERNAME"),
                            help="defaults to env[OS_USERNAME]")

        parser.add_argument("--os-password",
                            metavar="<auth-password>",
                            default=os.environ.get("OS_PASSWORD"),
                            help="defaults to env[OS_PASSWORD]")

        parser.add_argument("--os-user-domain-id",
                            metavar="<auth-user-domain-id>",
                            default=os.environ.get("OS_USER_DOMAIN_ID"),
                            help="defaults to env[OS_USER_DOMAIN_ID]")

        parser.add_argument("--os-user-domain-name",
                            metavar="<auth-user-domain-name>",
                            default=os.environ.get("OS_USER_DOMAIN_NAME"),
                            help="defaults to env[OS_USER_DOMAIN_NAME]")

        parser.add_argument("--os-project-name",
                            metavar="<auth-project-name>",
                            default=os.environ.get("OS_PROJECT_NAME"),
                            help="defaults to env[OS_PROJECT_NAME]")

        parser.add_argument("--os-project-id",
                            metavar="<auth-project-id>",
                            default=os.environ.get("OS_PROJECT_ID"),
                            help="defaults to env[OS_PROJECT_ID]")

        parser.add_argument("--os-project-domain-id",
                            metavar="<auth-project-domain-id>",
                            default=os.environ.get("OS_PROJECT_DOMAIN_ID"),
                            help="defaults to env[OS_PROJECT_DOMAIN_ID]")

        parser.add_argument("--os-project-domain-name",
                            metavar="<auth-project-domain-name>",
                            default=os.environ.get("OS_PROJECT_DOMAIN_NAME"),
                            help="defaults to env[OS_PROJECT_DOMAIN_NAME]")

        parser.add_argument("--os-auth-token",
                            metavar="<auth-token>",
                            default=os.environ.get("OS_AUTH_TOKEN", None),
                            help="defaults to env[OS_AUTH_TOKEN]")

        parser.add_argument('--os-auth-token-cache',
                            default=os.environ.get("OS_AUTH_TOKEN_CACHE",
                                                   False),
                            action='store_true',
                            help="Use the auth token cache. Defaults to False "
                                 "if env[OS_AUTH_TOKEN_CACHE] is not set")

        parser.add_argument("--os-auth-url",
                            metavar="<auth-url>",
                            default=os.environ.get("OS_AUTH_URL"),
                            help="defaults to env[OS_AUTH_URL]")

        parser.add_argument("--os-access-token",
                            metavar="<token>",
                            default=os.environ.get("OS_ACCESS_TOKEN"),
                            help="defaults to env[OS_ACCESS_TOKEN]")

        parser.add_argument("--os-auth-type",
                            metavar="<auth-type>",
                            default=os.environ.get("OS_AUTH_TYPE", "password"),
                            help="defaults to env[OS_AUTH_TYPE]")

        parser.add_argument("--os-auth-system",
                            metavar="<auth-system>",
                            default=os.environ.get("OS_AUTH_SYSTEM"),
                            help="defaults to env[OS_AUTH_SYSTEM]")

        parser.add_argument("--bypass-url",
                            metavar="<bypass-url>",
                            dest="bypass_url",
                            help="use this API endpoint instead of the "
                                 "Service Catalog")

        parser.add_argument("--os-ca-cert",
                            metavar="<ca-certificate>",
                            default=os.environ.get("OS_CACERT", None),
                            help="Specify a CA bundle file to use in verifying"
                                 " a TLS (https) server certificate. Defaults "
                                 "to env[OS_CACERT]")

        parser.add_argument("--egi-checkin-url",
                            metavar="<egi-checkin-url>",
                            default=os.environ.get("EGI_CHECKIN_URL", "https://aai.egi.eu"),
                            help="Specify the EGI checkin URL. Defaults "
                                 "to env[EGI_CHECKIN_URL]")

        parser.add_argument("--egi-checkin-client-id",
                            metavar="<egi-checkin-client-id>",
                            default=os.environ.get("EGI_CHECKIN_CLIENT_ID", None),
                            help="Specify your EGI checkin client ID. Defaults "
                                 "to env[EGI_CHECKIN_CLIENT_ID]")

        parser.add_argument("--egi-checkin-client-secret",
                            metavar="<egi-checkin-client-secret>",
                            default=os.environ.get("EGI_CHECKIN_CLIENT_SECRET", None),
                            help="Specify your EGI checkin client secret. Defaults "
                                 "to env[EGI_CHECKIN_CLIENT_SECRET]")

        parser.add_argument("--egi-checkin-refresh-token",
                            metavar="<egi-checkin-refresh-token>",
                            default=os.environ.get("EGI_CHECKIN_REFRESH_TOKEN", None),
                            help="Specify your EGI refresh token. Defaults "
                                 "to env[EGI_CHECKIN_REFRESH_TOKEN]")

        parser.add_argument("--voms-proxy",
                            metavar="<voms-proxy>",
                            default=os.environ.get("VOMS_PROXY", None),
                            help="Specify your VOMS proxy file. Defaults "
                                 "to env[VOMS_PROXY]")

        args = parser.parse_args(sys.argv[1:])

        os_username = args.os_username
        os_password = args.os_password
        os_user_domain_id = args.os_user_domain_id
        os_user_domain_name = args.os_user_domain_name
        os_project_id = args.os_project_id
        os_project_name = args.os_project_name
        os_project_domain_id = args.os_project_domain_id
        os_project_domain_name = args.os_project_domain_name
        os_auth_type = args.os_auth_type
        os_access_token = args.os_access_token
        os_auth_token = args.os_auth_token
        os_auth_token_cache = args.os_auth_token_cache
        os_auth_url = args.os_auth_url
        os_ca_cert = args.os_ca_cert
        bypass_url = args.bypass_url
        egi_checkin_url = args.egi_checkin_url
        egi_client_id = args.egi_checkin_client_id
        egi_client_secret = args.egi_checkin_client_secret
        egi_refresh_token = args.egi_checkin_refresh_token
        voms_proxy = args.voms_proxy

        token = None

        if not os_project_name and not os_project_id:
            raise Exception("os-project-name and os-project-id not defined!")

        if not os_auth_url:
            raise Exception("'os-auth-url' not defined!")

        if not os_user_domain_name:
            os_user_domain_name = "default"

        if not os_project_domain_name:
            os_project_domain_name = "default"

        if os_auth_type == "password":
            if not os_username:
                raise Exception("'os-username' not defined!")

            if not os_password:
                raise Exception("'os-password' not defined!")

            token = get_scoped_token(os_auth_url=os_auth_url,
                                     os_auth_type=os_auth_type,
                                     os_username=os_username,
                                     os_password=os_password,
                                     os_user_domain_id=os_user_domain_id,
                                     os_user_domain_name=os_user_domain_name,
                                     os_project_name=os_project_name,
                                     os_project_domain_id=os_project_domain_id,
                                     os_project_domain_name=os_project_domain_name,
                                     os_ca_cert=os_ca_cert)
        else:
            """
            if not egi_checkin_url:
                raise Exception("'egi_checkin_url' not defined!")

            if not egi_client_id:
                raise Exception("'egi_client_id' not defined!")

            if not egi_client_secret:
                raise Exception("'egi_client_secret' not defined!")
            """
            if egi_client_id and egi_client_secret and egi_refresh_token:
                if not os_access_token:
                    os_access_token = get_access_token(egi_checkin_url,
                                                       egi_client_id,
                                                       egi_client_secret,
                                                       egi_refresh_token)

                    if not os_access_token:
                        raise Exception("cannot get the EGI access_token!")

                unscoped_token = get_unscoped_token(os_auth_url, access_token=os_access_token)
            elif voms_proxy:
                unscoped_token = get_unscoped_token(os_auth_url, voms_proxy=voms_proxy)
            else:
                raise Exception("found wrong token parameters")

            token = get_scoped_token(os_auth_url=os_auth_url,
                                     os_auth_type=os_auth_type,
                                     os_project_id=os_project_id,
                                     unscoped_token=unscoped_token,
                                     os_ca_cert=os_ca_cert)

        result = {"apiVersion": "client.authentication.k8s.io/v1beta1",
                  "kind": "ExecCredential",
                  "user": token.getUser()["name"],
                  "status": {
                      "token": token.getId()
                  }
                 }
        print(json.dumps(result))
    except Exception as e:
        print("ERROR: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
