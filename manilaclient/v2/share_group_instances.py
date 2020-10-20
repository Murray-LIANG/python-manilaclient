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

RESOURCES_PATH = '/share-group-instances'
RESOURCE_PATH = '/share-group-instances/%s'
RESOURCE_PATH_ACTION = '/share-group-instances/%s/action'
RESOURCES_NAME = 'share_group_instances'
RESOURCE_NAME = 'share_group_instance'


class ShareGroupInstance(common_base.Resource):
    """A instance of a share group."""

    def __repr__(self):
        return "<Share Group Instance: %s>" % self.id

    def force_delete(self):
        """Force-delete this share group instance."""
        self.manager.force_delete(self)

    def reset_state(self, state):
        """Reset `status` attr of this share group instance."""
        self.manager.reset_state(self, state)

    def reset_replica_state(self, replica_state):
        """Reset `replica_state` attr of this share group instance."""
        self.manager.reset_replica_state(self, replica_state)


class ShareGroupInstanceManager(base.ManagerWithFind):
    """Manage :class:`ShareGroupInstance` resources."""
    resource_class = ShareGroupInstance

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def get(self, share_group_instance):
        """Get a share group instance.

        :param share_group_instance: either share group instance object or text
            with its UUID.
        :rtype: :class:`ShareGroupInstance`
        """
        share_group_instance_id = common_base.getid(share_group_instance)
        url = RESOURCE_PATH % share_group_instance_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def list(self, share_group=None, detailed=True, search_opts=None,
             sort_key=None, sort_dir=None):
        """Get a list of all share group instances belonging to share group.

        :param share_group: either ShareGroup object or text with its UUID.
        :param detailed: Whether to return detailed instances info or not.
        :param search_opts: dict with search options to filter out instances.
            available keys are below (('name1', 'name2', ...), 'type'):
            - ('all_tenants', int)
            - ('replica_state', text)
            - ('status', text)
            - ('limit', int)
            - ('offset', int)
        :param sort_key: Key to be sorted (i.e. 'created_at' or 'status').
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`ShareGroupInstance`
        """

        search_opts = search_opts or {}

        if share_group:
            search_opts['share_group_id'] = common_base.getid(share_group)

        if sort_key is not None:
            if sort_key in constants.SHARE_GROUP_INSTANCE_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
            else:
                msg = 'sort_key must be one of the following: %s.'
                msg_args = ', '.join(
                    constants.SHARE_GROUP_INSTANCE_SORT_KEY_VALUES)
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

    def _action(self, share_group_instance, action, info=None):
        """Perform `action` on the specified share group instance.

        :param share_group_instance: either ShareGroupInstance object or text
            with its UUID.
        :param action: text with action name.
        :param info: dict with data for the action.
        """
        share_group_instance_id = common_base.getid(share_group_instance)
        url = RESOURCE_PATH_ACTION % share_group_instance_id
        body = {action: info}
        self.api.client.post(url, body=body)

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def force_delete(self, share_group_instance):
        """Force-delete a share group instance.

        :param share_group_instance: either ShareGroupInstance object or text
            with its UUID.
        """
        self._action(share_group_instance, 'force_delete')

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def reset_state(self, share_group_instance, state):
        """Reset `status` attr of the specified share group instance.

        :param share_group_instance: either ShareGroupInstance object or text
            with its UUID.
        :param state: The new state for the share group instance.
        """
        self._action(share_group_instance, 'reset_status',
                     info={'status': state})

    @api_versions.wraps("2.56")
    @api_versions.experimental_api
    def reset_replica_state(self, share_group_instance, replica_state):
        """Reset `replica_state` attr of the specified share group instance.

        :param share_group_instance: either ShareGroupInstance object or text
            with its UUID.
        :param replica_state: The new replica_state for the share group
            instance.
        """
        self._action(share_group_instance, 'reset_replica_state',
                     {'replica_state': replica_state})
