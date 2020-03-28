# Copyright 2020 Ryan Liang
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

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common import constants
from manilaclient.common.apiclient import base as common_base

RESOURCES_PATH = '/share-group-replicas'
RESOURCE_PATH = '/share-group-replicas/%s'
RESOURCE_PATH_ACTION = '/share-group-replicas/%s/action'
RESOURCES_NAME = 'share_group_replicas'
RESOURCE_NAME = 'share_group_replica'


class ShareGroupReplica(common_base.Resource):
    """A replica of a share group."""

    def __repr__(self):
        return "<Share Group Replica: %s>" % self.id

    def delete(self):
        """Delete this share group replica."""
        self.manager.delete(self)

    def reset_state(self, state):
        """Reset `status` attr of this share group replica."""
        self.manager.reset_state(self, state)

    def promote(self):
        """Promote the specified share group replica."""
        self.manager.promote(self)

    def resync(self):
        """Re-sync the specified share group replica."""
        self.manager.resync(self)

    def reset_replica_state(self, replica_state):
        """Reset `replica_state` attr of this share group replica."""
        self.manager.reset_replica_state(self, replica_state)


class ShareGroupReplicaManager(base.ManagerWithFind):
    """Manage :class:`ShareGroupReplica` resources."""
    resource_class = ShareGroupReplica

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def create(self, share_group):
        """Create a share group replica.

        :param share_group: either ShareGroup object or text with its UUID.
        :rtype: :class:`ShareGroupReplica`
        """
        share_group_id = common_base.getid(share_group)
        body = {'share_group_id': share_group_id}

        return self._create(RESOURCES_PATH,
                            {RESOURCE_NAME: body},
                            RESOURCE_NAME)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def get(self, share_group_replica):
        """Get a share group replica.

        :param share_group_replica: either share group replica object or text
            with its UUID.
        :rtype: :class:`ShareGroupReplica`
        """
        share_group_replica_id = common_base.getid(share_group_replica)
        url = RESOURCE_PATH % share_group_replica_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def list(self, share_group=None, detailed=True, search_opts=None,
             sort_key=None, sort_dir=None):
        """Get a list of all share group replicas belonging to share group.

        :param share_group: either ShareGroup object or text with its UUID.
        :param detailed: Whether to return detailed replica info or not.
        :param search_opts: dict with search options to filter out replicas.
            available keys are below (('name1', 'name2', ...), 'type'):
            - ('all_tenants', int)
            - ('offset', int)
            - ('limit', int)
            - ('name', text)
            - ('status', text)
            - ('share_group_id', text)
        :param sort_key: Key to be sorted (i.e. 'created_at' or 'status').
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`ShareGroupReplica`
        """

        search_opts = search_opts or {}

        if share_group:
            search_opts['share_id'] = common_base.getid(share_group)

        if sort_key is not None:
            if sort_key in constants.SHARE_GROUP_REPLICA_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
            else:
                msg = 'sort_key must be one of the following: %s.'
                msg_args = ', '.join(
                    constants.SHARE_GROUP_REPLICA_SORT_KEY_VALUES)
                raise ValueError(msg % msg_args)

        if sort_dir is not None:
            if sort_dir in constants.SORT_DIR_VALUES:
                search_opts['sort_dir'] = sort_dir
            else:
                raise ValueError('sort_dir must be one of the following: %s.'
                                 % ', '.join(constants.SORT_DIR_VALUES))

        query_string = self._build_query_string(search_opts)

        if detailed:
            url = RESOURCES_PATH + '/detail' + query_string
        else:
            url = RESOURCES_PATH + query_string

        return self._list(url, RESOURCES_NAME)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def delete(self, share_group_replica, force=False):
        """Delete a share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        :param force: True to force the deletion.
        """
        share_group_replica_id = common_base.getid(share_group_replica)
        if force:
            url = RESOURCE_PATH_ACTION % share_group_replica_id
            body = {'force_delete': None}
            self.api.client.post(url, body=body)
        else:
            url = RESOURCE_PATH % share_group_replica_id
            self._delete(url)

    def _action(self, share_group_replica, action, info=None):
        """Perform `action` on the specified share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        :param action: text with action name.
        :param info: dict with data for the action.
        """
        share_group_replica_id = common_base.getid(share_group_replica)
        url = RESOURCE_PATH_ACTION % share_group_replica_id
        body = {action: info}
        self.api.client.post(url, body=body)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def reset_state(self, share_group_replica, state):
        """Reset `status` attr of the specified share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        :param state: The new state for the share group replica.
        """
        self._action(share_group_replica, 'reset_status',
                     info={'status': state})

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def promote(self, share_group_replica):
        """Promote the specified share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        """
        self._action(share_group_replica, 'promote')

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def resync(self, share_group_replica):
        """Re-sync the specified share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        """
        self._action(share_group_replica, 'resync')

    @api_versions.wraps("2.11")
    @api_versions.experimental_api
    def reset_replica_state(self, share_group_replica, replica_state):
        """Reset `replica_state` attr of the specified share group replica.

        :param share_group_replica: either ShareGroupReplica object or text
            with its UUID.
        :param replica_state: The new replica_state for the share group
            replica.
        """
        self._action(share_group_replica, 'reset_replica_state',
                     {'replica_state': replica_state})
