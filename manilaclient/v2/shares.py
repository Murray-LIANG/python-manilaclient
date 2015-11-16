# Copyright 2012 NetApp
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
"""Interface for shares extension."""

import collections
import re
try:
    from urllib import urlencode  # noqa
except ImportError:
    from urllib.parse import urlencode  # noqa

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common import constants
from manilaclient import exceptions
from manilaclient.openstack.common.apiclient import base as common_base
from manilaclient.v2 import share_instances


class Share(common_base.Resource):
    """A share is an extra block level storage to the OpenStack instances."""
    def __repr__(self):
        return "<Share: %s>" % self.id

    def update(self, **kwargs):
        """Update this share."""
        self.manager.update(self, **kwargs)

    def unmanage(self, **kwargs):
        """Unmanage this share."""
        self.manager.unmanage(self, **kwargs)

    def migrate_share(self, host, force_host_copy):
        """Migrate the share to a new host."""
        self.manager.migrate_share(self, host, force_host_copy)

    def delete(self, consistency_group_id=None):
        """Delete this share."""
        self.manager.delete(self, consistency_group_id=consistency_group_id)

    def force_delete(self):
        """Delete the specified share ignoring its current state."""
        self.manager.force_delete(self)

    def allow(self, access_type, access, access_level):
        """Allow access to a share."""
        self._validate_access(access_type, access)
        return self.manager.allow(self, access_type, access, access_level)

    def deny(self, id):
        """Deny access from IP to a share."""
        return self.manager.deny(self, id)

    def access_list(self):
        """Deny access from IP to a share."""
        return self.manager.access_list(self)

    def _validate_access(self, access_type, access):
        if access_type == 'ip':
            self._validate_ip_range(access)
        elif access_type == 'user':
            self._validate_username(access)
        elif access_type == 'cert':
            # 'access' is used as the certificate's CN (common name)
            # to which access is allowed or denied by the backend.
            # The standard allows for just about any string in the
            # common name. The meaning of a string depends on its
            # interpretation and is limited to 64 characters.
            self._validate_common_name(access.strip())
        else:
            raise exceptions.CommandError(
                'Only ip, user, and cert types are supported')

    def update_all_metadata(self, metadata):
        """Update all metadata of this share."""
        return self.manager.update_all_metadata(self, metadata)

    @staticmethod
    def _validate_common_name(access):
        if len(access) == 0 or len(access) > 64:
            exc_str = ('Invalid CN (common name). Must be 1-64 chars long.')
            raise exceptions.CommandError(exc_str)

    @staticmethod
    def _validate_username(access):
        valid_username_re = '[\w\.\-_\`;\'\{\}\[\]\\\\]{4,32}$'
        username = access
        if not re.match(valid_username_re, username):
            exc_str = ('Invalid user or group name. Must be 4-32 characters '
                       'and consist of alphanumeric characters and '
                       'special characters ]{.-_\'`;}[\\')
            raise exceptions.CommandError(exc_str)

    @staticmethod
    def _validate_ip_range(ip_range):
        ip_range = ip_range.split('/')
        exc_str = ('Supported ip format examples:\n'
                   '\t10.0.0.2, 10.0.0.0/24')
        if len(ip_range) > 2:
            raise exceptions.CommandError(exc_str)
        if len(ip_range) == 2:
            try:
                prefix = int(ip_range[1])
                if prefix < 0 or prefix > 32:
                    raise ValueError()
            except ValueError:
                msg = 'IP prefix should be in range from 0 to 32'
                raise exceptions.CommandError(msg)
        ip_range = ip_range[0].split('.')
        if len(ip_range) != 4:
            raise exceptions.CommandError(exc_str)
        for item in ip_range:
            try:
                if 0 <= int(item) <= 255:
                    continue
                raise ValueError()
            except ValueError:
                raise exceptions.CommandError(exc_str)

    def reset_state(self, state):
        """Update the share with the provided state."""
        self.manager.reset_state(self, state)

    def extend(self, new_size):
        """Extend the size of the specified share."""
        self.manager.extend(self, new_size)

    def shrink(self, new_size):
        """Shrink the size of the specified share."""
        self.manager.shrink(self, new_size)

    def list_instances(self):
        """List instances of the specified share."""
        self.manager.list_instances(self)


class ShareManager(base.ManagerWithFind):
    """Manage :class:`Share` resources."""
    resource_class = Share

    def create(self, share_proto, size, snapshot_id=None, name=None,
               description=None, metadata=None, share_network=None,
               share_type=None, is_public=False, availability_zone=None,
               consistency_group_id=None):
        """Create a share.

        :param share_proto: text - share protocol for new share
            available values are NFS, CIFS, GlusterFS and HDFS.
        :param size: int - size in GB
        :param snapshot_id: text - ID of the snapshot
        :param name: text - name of new share
        :param description: text - description of a share
        :param metadata: dict - optional metadata to set on share creation
        :param share_network: either instance of ShareNetwork or text with ID
        :param share_type: either instance of ShareType or text with ID
        :param is_public: bool, whether to set share as public or not.
        :param consistency_group_id: text - ID of the consistency group to
            which the share should belong
        :rtype: :class:`Share`
        """
        share_metadata = metadata if metadata is not None else dict()
        body = {
            'size': size,
            'snapshot_id': snapshot_id,
            'name': name,
            'description': description,
            'metadata': share_metadata,
            'share_proto': share_proto,
            'share_network_id': common_base.getid(share_network),
            'share_type': common_base.getid(share_type),
            'is_public': is_public,
            'availability_zone': availability_zone,
            'consistency_group_id': consistency_group_id,
        }
        return self._create('/shares', {'share': body}, 'share')

    def _do_migrate_share(self, share, host, force_host_copy, action_name):
        """Migrate share to new host and pool.

        :param share: The :class:'share' to migrate
        :param host: The destination host and pool
        :param force_host_copy: Skip driver optimizations
        """

        return self._action(
            action_name, share,
            {"host": host, "force_host_copy": force_host_copy})

    @api_versions.wraps("2.5", "2.6")
    def migrate_share(self, share, host, force_host_copy):
        return self._do_migrate_share(
            share, host, force_host_copy, "os-migrate_share")

    @api_versions.wraps("2.7")  # noqa
    def migrate_share(self, share, host, force_host_copy):
        return self._do_migrate_share(
            share, host, force_host_copy, "migrate_share")

    def _do_manage(self, service_host, protocol, export_path,
                   driver_options=None, share_type=None,
                   name=None, description=None,
                   resource_path="/shares/manage"):
        """Manage some existing share.

        :param service_host: text - host of share service where share is runing
        :param protocol: text - share protocol that is used
        :param export_path: text - export path of share
        :param driver_options: dict - custom set of key-values.
        :param share_type: text - share type that should be used for share
        :param name: text - name of new share
        :param description: - description for new share
        """
        driver_options = driver_options if driver_options else dict()
        body = {
            'service_host': service_host,
            'share_type': share_type,
            'protocol': protocol,
            'export_path': export_path,
            'driver_options': driver_options,
            'name': name,
            'description': description
        }
        return self._create(resource_path, {'share': body}, 'share')

    @api_versions.wraps("1.0", "2.6")
    def manage(self, service_host, protocol, export_path, driver_options=None,
               share_type=None, name=None, description=None):
        return self._do_manage(
            service_host, protocol, export_path, driver_options, share_type,
            name, description, "/os-share-manage")

    @api_versions.wraps("2.7")  # noqa
    def manage(self, service_host, protocol, export_path, driver_options=None,
               share_type=None, name=None, description=None):
        return self._do_manage(
            service_host, protocol, export_path, driver_options, share_type,
            name, description, "/shares/manage")

    @api_versions.wraps("1.0", "2.6")
    def unmanage(self, share):
        """Unmanage a share.

        :param share: either share object or text with its ID.
        """
        return self.api.client.post(
            "/os-share-unmanage/%s/unmanage" % common_base.getid(share))

    @api_versions.wraps("2.7")  # noqa
    def unmanage(self, share):
        """Unmanage a share.

        :param share: either share object or text with its ID.
        """
        return self._action("unmanage", share)

    def get(self, share):
        """Get a share.

        :param share: either share object or text with its ID.
        :rtype: :class:`Share`
        """
        share_id = common_base.getid(share)
        return self._get("/shares/%s" % share_id, "share")

    def update(self, share, **kwargs):
        """Updates a share.

        :param share: either share object or text with its ID.
        :rtype: :class:`Share`
        """
        if not kwargs:
            return

        body = {'share': kwargs, }
        share_id = common_base.getid(share)
        return self._update("/shares/%s" % share_id, body)

    def list(self, detailed=True, search_opts=None,
             sort_key=None, sort_dir=None):
        """Get a list of all shares.

        :param detailed: Whether to return detailed share info or not.
        :param search_opts: dict with search options to filter out shares.
            available keys are below (('name1', 'name2', ...), 'type'):
            - ('all_tenants', int)
            - ('is_public', bool)
            - ('metadata', dict)
            - ('extra_specs', dict)
            - ('limit', int)
            - ('offset', int)
            - ('name', text)
            - ('status', text)
            - ('host', text)
            - ('share_server_id', text)
            - (('share_network_id', 'share_network'), text)
            - (('share_type_id', 'share_type'), text)
            - (('snapshot_id', 'snapshot'), text)
            Note, that member context will have restricted set of
            available search opts. For admin context filtering also available
            by each share attr from its Model. So, this list is not full for
            admin context.
        :param sort_key: Key to be sorted (i.e. 'created_at' or 'status').
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`Share`
        """
        if search_opts is None:
            search_opts = {}

        if sort_key is not None:
            if sort_key in constants.SHARE_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
                # NOTE(vponomaryov): Replace aliases with appropriate keys
                if sort_key == 'share_type':
                    search_opts['sort_key'] = 'share_type_id'
                elif sort_key == 'snapshot':
                    search_opts['sort_key'] = 'snapshot_id'
                elif sort_key == 'share_network':
                    search_opts['sort_key'] = 'share_network_id'
            else:
                raise ValueError('sort_key must be one of the following: %s.'
                                 % ', '.join(constants.SHARE_SORT_KEY_VALUES))

        if sort_dir is not None:
            if sort_dir in constants.SORT_DIR_VALUES:
                search_opts['sort_dir'] = sort_dir
            else:
                raise ValueError('sort_dir must be one of the following: %s.'
                                 % ', '.join(constants.SORT_DIR_VALUES))

        if 'is_public' not in search_opts:
            search_opts['is_public'] = True

        if search_opts:
            query_string = urlencode(
                sorted([(k, v) for (k, v) in list(search_opts.items()) if v]))
            if query_string:
                query_string = "?%s" % (query_string,)
        else:
            query_string = ''

        if detailed:
            path = "/shares/detail%s" % (query_string,)
        else:
            path = "/shares%s" % (query_string,)

        return self._list(path, 'shares')

    def delete(self, share, consistency_group_id=None):
        """Delete a share.

        :param share: either share object or text with its ID.
        :param consistency_group_id: text - ID of the consistency group to
            which the share belongs to.
        """
        url = "/shares/%s" % common_base.getid(share)
        if consistency_group_id:
            url += "?consistency_group_id=%s" % consistency_group_id
        self._delete(url)

    def _do_force_delete(self, share, action_name):
        """Delete a share forcibly - share status will be avoided.

        :param share: either share object or text with its ID.
        """
        return self._action(action_name, share)

    @api_versions.wraps("1.0", "2.6")
    def force_delete(self, share):
        return self._do_force_delete(share, "os-force_delete")

    @api_versions.wraps("2.7")  # noqa
    def force_delete(self, share):
        return self._do_force_delete(share, "force_delete")

    def _do_allow(self, share, access_type, access, access_level, action_name):
        """Allow access to a share.

        :param share: either share object or text with its ID.
        :param access_type: string that represents access type ('ip','domain')
        :param access: string that represents access ('127.0.0.1')
        :param access_level: string that represents access level ('rw', 'ro')
        """
        access_params = {
            'access_type': access_type,
            'access_to': access,
        }
        if access_level:
            access_params['access_level'] = access_level
        access = self._action(action_name, share,
                              access_params)[1]["access"]

        return access

    @api_versions.wraps("1.0", "2.6")
    def allow(self, share, access_type, access, access_level):
        return self._do_allow(
            share, access_type, access, access_level, "os-allow_access")

    @api_versions.wraps("2.7")  # noqa
    def allow(self, share, access_type, access, access_level):
        return self._do_allow(
            share, access_type, access, access_level, "allow_access")

    def _do_deny(self, share, access_id, action_name):
        """Deny access to a share.

        :param share: either share object or text with its ID.
        :param access_id: ID of share access rule
        """
        return self._action(action_name, share, {"access_id": access_id})

    @api_versions.wraps("1.0", "2.6")
    def deny(self, share, access_id):
        return self._do_deny(share, access_id, "os-deny_access")

    @api_versions.wraps("2.7")  # noqa
    def deny(self, share, access_id):
        return self._do_deny(share, access_id, "deny_access")

    def _do_access_list(self, share, action_name):
        """Get access list to a share.

        :param share: either share object or text with its ID.
        """
        access_list = self._action(action_name, share)[1]["access_list"]
        if access_list:
            t = collections.namedtuple('Access', list(access_list[0]))
            return [t(*value.values()) for value in access_list]
        else:
            return []

    @api_versions.wraps("1.0", "2.6")
    def access_list(self, share):
        return self._do_access_list(share, "os-access_list")

    @api_versions.wraps("2.7")  # noqa
    def access_list(self, share):
        return self._do_access_list(share, "access_list")

    def get_metadata(self, share):
        """Get metadata of a share.

        :param share: either share object or text with its ID.
        """
        return self._get("/shares/%s/metadata" % common_base.getid(share),
                         "metadata")

    def set_metadata(self, share, metadata):
        """Set or update metadata for share.

        :param share: either share object or text with its ID.
        :param metadata: A list of keys to be set.
        """
        body = {'metadata': metadata}
        return self._create("/shares/%s/metadata" % common_base.getid(share),
                            body, "metadata")

    def delete_metadata(self, share, keys):
        """Delete specified keys from shares metadata.

        :param share: either share object or text with its ID.
        :param keys: A list of keys to be removed.
        """
        share_id = common_base.getid(share)
        for key in keys:
            self._delete("/shares/%(share_id)s/metadata/%(key)s" % {
                'share_id': share_id, 'key': key})

    def update_all_metadata(self, share, metadata):
        """Update all metadata of a share.

        :param share: either share object or text with its ID.
        :param metadata: A list of keys to be updated.
        """
        body = {'metadata': metadata}
        return self._update("/shares/%s/metadata" % common_base.getid(share),
                            body)

    def _action(self, action, share, info=None, **kwargs):
        """Perform a share 'action'.

        :param action: text with action name.
        :param share: either share object or text with its ID.
        :param info: dict with data for specified 'action'.
        :param kwargs: dict with data to be provided for action hooks.
        """
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/shares/%s/action' % common_base.getid(share)
        return self.api.client.post(url, body=body)

    def _do_reset_state(self, share, state, action_name):
        """Update the provided share with the provided state.

        :param share: either share object or text with its ID.
        :param state: text with new state to set for share.
        """
        return self._action(action_name, share, {"status": state})

    @api_versions.wraps("1.0", "2.6")
    def reset_state(self, share, state):
        return self._do_reset_state(share, state, "os-reset_status")

    @api_versions.wraps("2.7")  # noqa
    def reset_state(self, share, state):
        return self._do_reset_state(share, state, "reset_status")

    def _do_extend(self, share, new_size, action_name):
        """Extend the size of the specified share.

        :param share: either share object or text with its ID.
        :param new_size: The desired size to extend share to.
        """
        return self._action(action_name, share, {"new_size": new_size})

    @api_versions.wraps("1.0", "2.6")
    def extend(self, share, new_size):
        return self._do_extend(share, new_size, "os-extend")

    @api_versions.wraps("2.7")  # noqa
    def extend(self, share, new_size):
        return self._do_extend(share, new_size, "extend")

    def _do_shrink(self, share, new_size, action_name):
        """Shrink the size of the specified share.

        :param share: either share object or text with its ID.
        :param new_size: The desired size to shrink share to.
        """
        return self._action(action_name, share, {'new_size': new_size})

    @api_versions.wraps("1.0", "2.6")
    def shrink(self, share, new_size):
        return self._do_shrink(share, new_size, "os-shrink")

    @api_versions.wraps("2.7")  # noqa
    def shrink(self, share, new_size):
        return self._do_shrink(share, new_size, "shrink")

    def list_instances(self, share):
        """List instances of the specified share.

        :param share: either share object or text with its ID.
        """
        return self._list(
            '/shares/%s/instances' % common_base.getid(share),
            'share_instances',
            obj_class=share_instances.ShareInstance
        )