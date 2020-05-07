"""
Copyright (c) 2020 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import absolute_import, unicode_literals

import copy
from collections import Counter

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from atomic_reactor.util import ImageName, chain_get
from atomic_reactor.utils.operator import OperatorCSV, OperatorManifest, NotOperatorCSV


yaml = YAML()


class PullSpec(object):
    def __init__(self, name, value, replace, path):
        self._name = name
        self._value = ImageName.parse(value)
        self._replace = ImageName.parse(replace)
        self._path = path

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def replace(self):
        return self._replace

    @property
    def path(self):
        return tuple(self._path)

    def __str__(self):
        return str(self.value)

    def find_in_data(self, data):
        return ImageName.parse(chain_get(data, self.path))


# Names based on location of pullspec:
#   RI = relatedImages
#   C = containers
#   CE = containers env
#   IC = initContainers
#   ICE = initContainers env
#   AN = annotations

RI1 = PullSpec(
    "ri1", "foo:1", "r-foo:2",
    ["spec", "relatedImages", 0, "image"]
)
RI2 = PullSpec(
    "ri2", "registry/bar:1", "r-registry/r-bar:2",
    ["spec", "relatedImages", 1, "image"]
)
C1 = PullSpec(
    "c1", "registry/namespace/spam:1", "r-registry/r-namespace/r-spam:2",
    ["spec", "install", "spec", "deployments", 0,
     "spec", "template", "spec", "containers", 0, "image"]
)
CE1 = PullSpec(
    "ce1", "eggs:1", "r-eggs:2",
    ["spec", "install", "spec", "deployments", 0,
     "spec", "template", "spec", "containers", 0, "env", 0, "value"]
)
C2 = PullSpec(
    "c2", "ham:1", "r-ham:2",
    ["spec", "install", "spec", "deployments", 0,
     "spec", "template", "spec", "containers", 1, "image"]
)
C3 = PullSpec(
    "c3", "jam:1", "r-jam:2",
    ["spec", "install", "spec", "deployments", 1,
     "spec", "template", "spec", "containers", 0, "image"]
)
AN1 = PullSpec(
    "an1", "registry/namespace/baz:latest", "r-registry/r-namespace/r-baz:latest",
    ["metadata", "annotations", "containerImage"]
)
IC1 = PullSpec(
    "ic1", "pullspec:1", "r-pullspec:1",
    ["spec", "install", "spec", "deployments", 1,
     "spec", "template", "spec", "initContainers", 0, "image"]
)
ICE1 = PullSpec(
    "ice1", "pullspec:2", "r-pullspec:2",
    ["spec", "install", "spec", "deployments", 1,
     "spec", "template", "spec", "initContainers", 0, "env", 0, "value"]
)

PULLSPECS = {p.name: p for p in [RI1, RI2, C1, CE1, C2, C3, AN1, IC1, ICE1]}


ORIGINAL_CONTENT = """\
# A meaningful comment
kind: ClusterServiceVersion
metadata:
  annotations:
    containerImage: {an1}
spec:
  relatedImages:
  - name: ri1
    image: {ri1}
  - name: ri2
    image: {ri2}
  install:
    spec:
      deployments:
      - spec:
          template:
            spec:
              containers:
              - name: c1
                image: {c1}
                env:
                - name: RELATED_IMAGE_CE1
                  value: {ce1}
                - name: UNRELATED_IMAGE
                  value: {ce1}
              - name: c2
                image: {c2}
      - spec:
          template:
            spec:
              containers:
              - name: c3
                image: {c3}
              initContainers:
              - name: ic1
                image: {ic1}
                env:
                - name: RELATED_IMAGE_ICE1
                  value: {ice1}
random:
  nested:
    dict:
      a: {ri1}
      b: {ri2}
      c: {c1}
      d: {ce1}
      e: {c2}
      f: {c3}
      g: {an1}
      h: {ic1}
      i: {ice1}
    list:
    - {ri1}
    - {ri2}
    - {c1}
    - {ce1}
    - {c2}
    - {c3}
    - {an1}
    - {ic1}
    - {ice1}
""".format(**PULLSPECS)

REPLACED_CONTENT = """\
# A meaningful comment
kind: ClusterServiceVersion
metadata:
  annotations:
    containerImage: {an1.replace}
spec:
  relatedImages:
  - name: ri1
    image: {ri1.replace}
  - name: ri2
    image: {ri2.replace}
  install:
    spec:
      deployments:
      - spec:
          template:
            spec:
              containers:
              - name: c1
                image: {c1.replace}
                env:
                - name: RELATED_IMAGE_CE1
                  value: {ce1.replace}
                - name: UNRELATED_IMAGE
                  value: {ce1}
              - name: c2
                image: {c2.replace}
      - spec:
          template:
            spec:
              containers:
              - name: c3
                image: {c3.replace}
              initContainers:
              - name: ic1
                image: {ic1.replace}
                env:
                - name: RELATED_IMAGE_ICE1
                  value: {ice1.replace}
random:
  nested:
    dict:
      a: {ri1}
      b: {ri2}
      c: {c1}
      d: {ce1}
      e: {c2}
      f: {c3}
      g: {an1}
      h: {ic1}
      i: {ice1}
    list:
    - {ri1}
    - {ri2}
    - {c1}
    - {ce1}
    - {c2}
    - {c3}
    - {an1}
    - {ic1}
    - {ice1}
""".format(**PULLSPECS)

REPLACED_EVERYWHERE_CONTENT = """\
# A meaningful comment
kind: ClusterServiceVersion
metadata:
  annotations:
    containerImage: {an1.replace}
spec:
  relatedImages:
  - name: ri1
    image: {ri1.replace}
  - name: ri2
    image: {ri2.replace}
  install:
    spec:
      deployments:
      - spec:
          template:
            spec:
              containers:
              - name: c1
                image: {c1.replace}
                env:
                - name: RELATED_IMAGE_CE1
                  value: {ce1.replace}
                - name: UNRELATED_IMAGE
                  value: {ce1.replace}
              - name: c2
                image: {c2.replace}
      - spec:
          template:
            spec:
              containers:
              - name: c3
                image: {c3.replace}
              initContainers:
              - name: ic1
                image: {ic1.replace}
                env:
                - name: RELATED_IMAGE_ICE1
                  value: {ice1.replace}
random:
  nested:
    dict:
      a: {ri1.replace}
      b: {ri2.replace}
      c: {c1.replace}
      d: {ce1.replace}
      e: {c2.replace}
      f: {c3.replace}
      g: {an1.replace}
      h: {ic1.replace}
      i: {ice1.replace}
    list:
    - {ri1.replace}
    - {ri2.replace}
    - {c1.replace}
    - {ce1.replace}
    - {c2.replace}
    - {c3.replace}
    - {an1.replace}
    - {ic1.replace}
    - {ice1.replace}
""".format(**PULLSPECS)


class CSVFile(object):
    def __init__(self, content):
        self.content = content
        self._data = yaml.load(content)

    @property
    def data(self):
        return copy.deepcopy(self._data)


ORIGINAL = CSVFile(ORIGINAL_CONTENT)
REPLACED = CSVFile(REPLACED_CONTENT)
REPLACED_EVERYWHERE = CSVFile(REPLACED_EVERYWHERE_CONTENT)


class TestOperatorCSV(object):
    _original_pullspecs = {p.value for p in PULLSPECS.values()}
    _replacement_pullspecs = {p.value: p.replace for p in PULLSPECS.values()}

    def test_wrong_kind(self):
        data = ORIGINAL.data

        del data["kind"]
        with pytest.raises(NotOperatorCSV) as exc_info:
            OperatorCSV("original.yaml", data)
        assert str(exc_info.value) == "Not a ClusterServiceVersion"

        data["kind"] = "ClusterResourceDefinition"
        with pytest.raises(NotOperatorCSV) as exc_info:
            OperatorCSV("original.yaml", data)
        assert str(exc_info.value) == "Not a ClusterServiceVersion"

    def test_from_file(self, tmpdir):
        path = tmpdir.join("original.yaml")
        path.write(ORIGINAL.content)

        csv = OperatorCSV.from_file(str(path))
        assert csv.path == str(path)
        assert csv.data == ORIGINAL.data

    def test_get_pullspecs(self, caplog):
        csv = OperatorCSV("original.yaml", ORIGINAL.data)
        pullspecs = csv.get_pullspecs()
        assert pullspecs == self._original_pullspecs

        expected_logs = [
            "original.yaml - Found pullspec for relatedImage ri1: {ri1}",
            "original.yaml - Found pullspec for relatedImage ri2: {ri2}",
            "original.yaml - Found pullspec for RELATED_IMAGE_CE1 var: {ce1}",
            "original.yaml - Found pullspec for RELATED_IMAGE_ICE1 var: {ice1}",
            "original.yaml - Found pullspec for container c1: {c1}",
            "original.yaml - Found pullspec for container c2: {c2}",
            "original.yaml - Found pullspec for container c3: {c3}",
            "original.yaml - Found pullspec for containerImage annotation: {an1}",
            "original.yaml - Found pullspec for initContainer ic1: {ic1}",
        ]
        for log in expected_logs:
            assert log.format(**PULLSPECS) in caplog.text

    def test_replace_pullspecs(self, caplog):
        csv = OperatorCSV("original.yaml", ORIGINAL.data)
        csv.replace_pullspecs(self._replacement_pullspecs)
        assert csv.data == REPLACED.data

        expected_logs = [
            "{file} - Replaced pullspec for relatedImage ri1: {ri1} -> {ri1.replace}",
            "{file} - Replaced pullspec for relatedImage ri2: {ri2} -> {ri2.replace}",
            "{file} - Replaced pullspec for RELATED_IMAGE_CE1 var: {ce1} -> {ce1.replace}",
            "{file} - Replaced pullspec for RELATED_IMAGE_ICE1 var: {ice1} -> {ice1.replace}",
            "{file} - Replaced pullspec for container c1: {c1} -> {c1.replace}",
            "{file} - Replaced pullspec for container c2: {c2} -> {c2.replace}",
            "{file} - Replaced pullspec for container c3: {c3} -> {c3.replace}",
            "{file} - Replaced pullspec for containerImage annotation: {an1} -> {an1.replace}",
            "{file} - Replaced pullspec for initContainer ic1: {ic1} -> {ic1.replace}",
        ]
        for log in expected_logs:
            assert log.format(file="original.yaml", **PULLSPECS) in caplog.text

    def test_replace_pullspecs_everywhere(self, caplog):
        csv = OperatorCSV("original.yaml", ORIGINAL.data)
        csv.replace_pullspecs_everywhere(self._replacement_pullspecs)
        assert csv.data == REPLACED_EVERYWHERE.data

        expected_logs = {
            "original.yaml - Replaced pullspec: {ri1} -> {ri1.replace}": 3,
            "original.yaml - Replaced pullspec: {ri2} -> {ri2.replace}": 3,
            "original.yaml - Replaced pullspec: {ce1} -> {ce1.replace}": 4,
            "original.yaml - Replaced pullspec: {c1} -> {c1.replace}": 3,
            "original.yaml - Replaced pullspec: {c2} -> {c2.replace}": 3,
            "original.yaml - Replaced pullspec: {c3} -> {c3.replace}": 3,
            "original.yaml - Replaced pullspec: {an1} -> {an1.replace}": 3,
            "original.yaml - Replaced pullspec: {ic1} -> {ic1.replace}": 3,
            "original.yaml - Replaced pullspec: {ice1} -> {ice1.replace}": 3,
        }
        for log, count in expected_logs.items():
            assert caplog.text.count(log.format(**PULLSPECS)) == count

    def test_dump(self, tmpdir):
        path = tmpdir.join("original.yaml")
        csv = OperatorCSV(str(path), ORIGINAL.data)
        csv.dump()

        content = path.read()
        # Formatting does not necessarily have to match, at least check the data...
        assert yaml.load(content) == csv.data
        # ...and that the comment was preserved
        assert content.startswith('# A meaningful comment')

    def test_replace_only_some_pullspecs(self, caplog):
        replacement_pullspecs = self._replacement_pullspecs.copy()

        # ri1 won't be replaced because replacement is identical
        replacement_pullspecs[RI1.value] = RI1.value
        # ri2 won't be replaced because no replacement available
        del replacement_pullspecs[RI2.value]

        csv = OperatorCSV("original.yaml", ORIGINAL.data)
        csv.replace_pullspecs(replacement_pullspecs)

        assert RI1.find_in_data(csv.data) == RI1.value
        assert RI2.find_in_data(csv.data) == RI2.value

        ri1_log = "original.yaml - Replaced pullspec for relatedImage ri1: {ri1}"
        ri2_log = "original.yaml - Replaced pullspec for relatedImage ri2: {ri2}"

        assert ri1_log.format(ri1=RI1) not in caplog.text
        assert ri2_log.format(ri2=RI2) not in caplog.text

    @pytest.mark.parametrize("rel_images", [True, False])
    @pytest.mark.parametrize("rel_envs, containers", [
        (False, False),
        (False, True),
        # (True, False) - Cannot have envs without containers
        (True, True),
    ])
    @pytest.mark.parametrize("annotations", [True, False])
    @pytest.mark.parametrize("init_rel_envs, init_containers", [
        (False, False),
        (False, True),
        # (True, False) - Cannot have initContainer envs without initContainers
        (True, True),
    ])
    def test_get_pullspecs_some_locations(self, rel_images, rel_envs, containers,
                                          annotations, init_rel_envs, init_containers):
        data = ORIGINAL.data
        expected = {p.value for p in PULLSPECS.values()}

        if not rel_images:
            expected -= {RI1.value, RI2.value}
            del data["spec"]["relatedImages"]
        deployments = chain_get(data, ["spec", "install", "spec", "deployments"])
        if not rel_envs:
            expected -= {CE1.value}
            for d in deployments:
                for c in chain_get(d, ["spec", "template", "spec", "containers"]):
                    c.pop("env", None)
        if not containers:
            expected -= {C1.value, C2.value, C3.value}
            for d in deployments:
                del d["spec"]["template"]["spec"]["containers"]
        if not annotations:
            expected -= {AN1.value}
            del data["metadata"]["annotations"]
        if not init_rel_envs:
            expected -= {ICE1.value}
            for d in deployments:
                for c in chain_get(d, ["spec", "template", "spec", "initContainers"], default=[]):
                    c.pop("env", None)
        if not init_containers:
            expected -= {IC1.value}
            for d in deployments:
                d["spec"]["template"]["spec"].pop("initContainers", None)

        csv = OperatorCSV("x.yaml", data)
        assert csv.get_pullspecs() == expected

    def test_valuefrom_references_not_allowed(self):
        data = ORIGINAL.data
        env_path = CE1.path[:-1]
        env = chain_get(data, env_path)
        env["valueFrom"] = "somewhere"

        csv = OperatorCSV("original.yaml", data)
        with pytest.raises(RuntimeError) as exc_info:
            csv.get_pullspecs()

        assert '"valueFrom" references are not supported' in str(exc_info.value)

    def test_set_related_images(self, caplog):
        data = ORIGINAL.data
        csv = OperatorCSV("original.yaml", data)
        csv.set_related_images()

        # the order is:
        #   1. existing relatedImages
        #   2. annotations
        #   3. containers
        #   4. initContainers
        #   5. container env vars
        #   6. initContainer env vars
        expected_related_images = [
            CommentedMap([("name", name), ("image", pullspec.value.to_str())])
            for name, pullspec in [
                ("ri1", RI1),
                ("ri2", RI2),
                ("baz-annotation", AN1),
                ("c1", C1),
                ("c2", C2),
                ("c3", C3),
                ("ic1", IC1),
                ("ce1", CE1),
                ("ice1", ICE1),
            ]
        ]
        assert csv.data["spec"]["relatedImages"] == expected_related_images

        expected_logs = [
            "{path} - Set relatedImage ri1 (from relatedImage ri1): {ri1}",
            "{path} - Set relatedImage ri2 (from relatedImage ri2): {ri2}",
            "{path} - Set relatedImage baz-annotation (from containerImage annotation): {an1}",
            "{path} - Set relatedImage c1 (from container c1): {c1}",
            "{path} - Set relatedImage c2 (from container c2): {c2}",
            "{path} - Set relatedImage c3 (from container c3): {c3}",
            "{path} - Set relatedImage ic1 (from initContainer ic1): {ic1}",
            "{path} - Set relatedImage ce1 (from RELATED_IMAGE_CE1 var): {ce1}",
            "{path} - Set relatedImage ice1 (from RELATED_IMAGE_ICE1 var): {ice1}",
        ]
        for log in expected_logs:
            assert log.format(path="original.yaml", **PULLSPECS) in caplog.text

    @pytest.mark.parametrize("related_images, containers, err_msg", [
        (
            # conflict in original relatedImages
            [{"name": "foo", "image": "foo"}, {"name": "foo", "image": "bar"}],
            [],
            ("{path} - Found conflicts when setting relatedImages:\n"
             "relatedImage foo: foo X relatedImage foo: bar")
        ),
        (
            # conflict in new relatedImages
            [],
            [{"name": "foo", "image": "foo"}, {"name": "foo", "image": "bar"}],
            ("{path} - Found conflicts when setting relatedImages:\n"
             "container foo: foo X container foo: bar")
        ),
        (
            # conflict between original and new relatedImages
            [{"name": "foo", "image": "foo"}],
            [{"name": "foo", "image": "bar"}],
            ("{path} - Found conflicts when setting relatedImages:\n"
             "relatedImage foo: foo X container foo: bar")
        ),
        (
            # duplicate in original relatedImages, no conflict
            [{"name": "foo", "image": "foo"}, {"name": "foo", "image": "foo"}],
            [],
            None
        ),
        (
            # duplicate in new relatedImages, no conflict
            [],
            [{"name": "foo", "image": "foo"}, {"name": "foo", "image": "foo"}],
            None
        ),
        (
            # duplicate between original and new relatedImages, no conflict
            [{"name": "foo", "image": "foo"}],
            [{"name": "foo", "image": "foo"}],
            None
        ),
        (
            # multiple conflicts in original and new relatedImages
            [{"name": "foo", "image": "foo"}, {"name": "foo", "image": "bar"}],
            [{"name": "foo", "image": "baz"}, {"name": "foo", "image": "spam"}],
            # all messages should be (first found pullspec X conflicting pullspec)
            ("{path} - Found conflicts when setting relatedImages:\n"
             "relatedImage foo: foo X relatedImage foo: bar\n"
             "relatedImage foo: foo X container foo: baz\n"
             "relatedImage foo: foo X container foo: spam")
        )
    ])
    def test_set_related_images_conflicts(self, related_images, containers, err_msg):
        data = {
            "kind": "ClusterServiceVersion",
            "spec": {
                "relatedImages": related_images,
                "install": {
                    "spec": {
                        "deployments": [
                            {
                                "spec": {
                                    "template": {
                                        "spec": {
                                            "containers": containers
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        csv = OperatorCSV("original.yaml", data)

        if err_msg is not None:
            with pytest.raises(RuntimeError) as exc_info:
                csv.set_related_images()
            assert str(exc_info.value) == err_msg.format(path="original.yaml")
        else:
            csv.set_related_images()
            updated_counts = Counter(x['name'] for x in csv.data['spec']['relatedImages'])
            # check that there are no duplicates in .spec.relatedImages
            for name, count in updated_counts.items():
                assert count == 1, 'Duplicate in relatedImages: {}'.format(name)

    @pytest.mark.parametrize('pullspecs, does_have', [
        (None, False),
        ([], False),
        ({'name': 'foo', 'image': 'bar'}, True),
    ])
    def test_has_related_images(self, pullspecs, does_have):
        data = {
            'kind': 'ClusterServiceVersion',
            'spec': {}
        }
        if pullspecs is not None:
            data['spec']['relatedImages'] = pullspecs
        csv = OperatorCSV('original.yaml', data)
        assert csv.has_related_images() == does_have

    @pytest.mark.parametrize('var, does_have', [
        (None, False),
        ({'name': 'UNRELATED_IMAGE', 'value': 'foo'}, False),
        ({'name': 'RELATED_IMAGE_BAR', 'value': 'baz'}, True),
    ])
    def test_has_related_image_envs(self, var, does_have):
        data = {
            'kind': 'ClusterServiceVersion',
            'spec': {
                'install': {
                    'spec': {
                        'deployments': [
                            {
                                'spec': {
                                    'template': {
                                        'spec': {
                                            'containers': [
                                                {'name': 'spam', 'image': 'eggs', 'env': []}
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        if var is not None:
            deployment = data['spec']['install']['spec']['deployments'][0]
            deployment['spec']['template']['spec']['containers'][0]['env'].append(var)
        csv = OperatorCSV('original.yaml', data)
        assert csv.has_related_image_envs() == does_have


class TestOperatorManifest(object):
    def test_from_directory(self, tmpdir):
        subdir = tmpdir.mkdir("nested")

        original = tmpdir.join("original.yaml")
        original.write(ORIGINAL.content)
        replaced = subdir.join("replaced.yaml")
        replaced.write(REPLACED.content)

        manifest = OperatorManifest.from_directory(str(tmpdir))

        original_csv = manifest.files[0]
        replaced_csv = manifest.files[1]

        assert original_csv.path == str(original)
        assert replaced_csv.path == str(replaced)

        assert original_csv.data == ORIGINAL.data
        assert replaced_csv.data == REPLACED.data

    def test_from_directory_no_csvs(self, tmpdir):
        subdir = tmpdir.mkdir("nested")

        original = tmpdir.join("original.yaml")
        replaced = subdir.join("replaced.yaml")

        original_data = ORIGINAL.data
        original_data["kind"] = "IDK"
        with open(str(original), "w") as f:
            yaml.dump(original_data, f)

        replaced_data = REPLACED.data
        del replaced_data["kind"]
        with open(str(replaced), "w") as f:
            yaml.dump(replaced_data, f)

        manifest = OperatorManifest.from_directory(str(tmpdir))
        assert manifest.files == []

    def test_directory_does_not_exist(self, tmpdir):
        nonexistent = tmpdir.join("nonexistent")

        with pytest.raises(RuntimeError) as exc_info:
            OperatorManifest.from_directory(str(nonexistent))

        msg = "Path does not exist or is not a directory: {}".format(nonexistent)
        assert str(exc_info.value) == msg

        regular_file = tmpdir.join("some_file")
        regular_file.write("hello")

        with pytest.raises(RuntimeError) as exc_info:
            OperatorManifest.from_directory(str(regular_file))

        msg = "Path does not exist or is not a directory: {}".format(regular_file)
        assert str(exc_info.value) == msg