"""
Copyright (c) 2017 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""
from __future__ import print_function, unicode_literals

from atomic_reactor.constants import INSPECT_CONFIG
from atomic_reactor.plugin import PreBuildPlugin
from atomic_reactor.constants import PLUGIN_KOJI_PARENT_KEY
from atomic_reactor.plugins.pre_reactor_config import get_koji_session
from osbs.utils import Labels

import time


DEFAULT_POLL_TIMEOUT = 60 * 10  # 10 minutes
DEFAULT_POLL_INTERVAL = 10  # 10 seconds


class KojiParentPlugin(PreBuildPlugin):
    """Wait for Koji build of parent image to be avaialable

    Uses inspected parent image config to determine the
    nvr (Name-Version-Release) of the parent image. It uses
    this information to check if the corresponding Koji
    build exists. This check is performed periodically until
    the Koji build is found, or timeout expires.

    This check is required due to a timing issue that may
    occur after the image is pushed to registry, but it
    has not been yet uploaded and tagged in Koji. This plugin
    ensures that the layered image is only built with a parent
    image that is known in Koji.
    """

    key = PLUGIN_KOJI_PARENT_KEY
    is_allowed_to_fail = False

    def __init__(self, tasker, workflow, koji_hub=None, koji_ssl_certs_dir=None,
                 poll_interval=DEFAULT_POLL_INTERVAL, poll_timeout=DEFAULT_POLL_TIMEOUT):
        """
        :param tasker: DockerTasker instance
        :param workflow: DockerBuildWorkflow instance
        :param koji_hub: str, koji hub (xmlrpc)
        :param koji_ssl_certs_dir: str, path to "cert", "ca", and "serverca"
                                   used when Koji's identity certificate is not trusted
        :param poll_interval: int, seconds between polling for Koji build
        :param poll_timeout: int, max amount of seconds to wait for Koji build
        """
        super(KojiParentPlugin, self).__init__(tasker, workflow)

        self.koji_fallback = {
            'hub_url': koji_hub,
            'auth': {'ssl_certs_dir': koji_ssl_certs_dir}
        }
        self.koji_session = get_koji_session(self.workflow, self.koji_fallback)

        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

        self._parent_image_nvr = None
        self._parent_image_build = None
        self._poll_start = None

    def run(self):
        if not self.detect_parent_image_nvr():
            return
        self.wait_for_parent_image_build()
        self.verify_parent_image_build()
        return self.make_result()

    def detect_parent_image_nvr(self):
        config = self.workflow.base_image_inspect[INSPECT_CONFIG]
        labels = Labels(config['Labels'] or {})

        label_names = [Labels.LABEL_TYPE_COMPONENT, Labels.LABEL_TYPE_VERSION,
                       Labels.LABEL_TYPE_RELEASE]
        label_values = []

        for lbl_name in label_names:
            try:
                _, lbl_value = labels.get_name_and_value(lbl_name)
                label_values.append(lbl_value)
            except KeyError:
                self.log.info("Failed to find label '%s' in parent image.",
                              labels.get_name(lbl_name))

        if len(label_values) != len(label_names):
            self._parent_image_nvr = None
            self.log.info("Not waiting for Koji build.")
            return False

        self._parent_image_nvr = '-'.join(label_values)
        return True

    def wait_for_parent_image_build(self):
        self.start_polling_timer()
        self.log.info('Waiting for parent image Koji build %s', self._parent_image_nvr)
        while self.is_within_timeout():
            if self.has_parent_image_build():
                self.log.info('Parent image Koji build found')
                break
            time.sleep(self.poll_interval)

    def start_polling_timer(self):
        self._poll_start = time.time()

    def is_within_timeout(self):
        return (time.time() - self._poll_start) < self.poll_timeout

    def has_parent_image_build(self):
        self._parent_image_build = self.koji_session.getBuild(self._parent_image_nvr)
        return self._parent_image_build is not None

    def verify_parent_image_build(self):
        if self._parent_image_build is None:
            raise ValueError('Parent image Koji build NOT found!')

    def make_result(self):
        return {
            'parent-image-koji-build': self._parent_image_build,
        }
