#!/usr/bin/env python3
#coding:utf-8
"""
  Author:  gemisigo --<gemisigo@gmail.com>
  Purpose: Class for building version documentation
  Created: 2022-05-28 15:59:36
"""
import os

from TodoReview.patterns import object_pattern, version_list_pattern, version_entry_pattern, version_pattern
from TodoReview.types import TYPES


class BuildVersionDoc:
    """

    Attributes
    ----------
            attribute: type
                    description

    Methods
    -------
            method(params: type)
                    description
    """

    def __init__(self, a_source_paths: list, a_target_path: str, a_project_path: str):
        """Constructor"""

        self.source_paths = a_source_paths
        self.target_path = a_target_path
        self.debug = True
        self.project_path = a_project_path

        o, v, p, s = self.collect_objects_and_versions()
        self.save_changelog_by_object(o)
        self.save_changelog_by_version(v)

    def collect_objects_and_versions(self) -> None:
        """Collect object and version data from the files on the given path"""

        objects = {}
        versions = {}
        files_processed = []
        files_skipped = []

        for path in self.source_paths:
            if not os.path.isabs(path):
                path = os.path.join(self.project_path, path)
                print(f'{path=}')
            for root, dirs, files in os.walk(path):
                for file in files:
                    print(f"processing file {file=}")
                    match = object_pattern.match(file)
                    if match:
                        files_processed.append(os.path.join(root, file))
                        object_type = TYPES[match.group('type')]
                        schema = match.group("schema")
                        object_name = match.group("object")
                        with open(os.path.join(root, file), "r", encoding="iso-8859-2") as f:
                            contents = f.read()
                            version_list_match = version_list_pattern.search(contents)
                            version_entries = version_list_match.group(
                                "versions").strip() if version_list_match else None
                            if version_entries:
                                if not object_type in objects:
                                    objects[object_type] = {}
                                if not schema in objects[object_type]:
                                    objects[object_type][schema] = {}
                                if not object_name in objects[object_type][schema]:
                                    objects[object_type][schema][object_name] = {
                                        "file": file, "versions": version_entries}

                                version_matches = version_entry_pattern.findall(
                                    version_entries)
                                for vms in version_matches:
                                    date = vms[0].strip()
                                    author = vms[1].strip()
                                    vm = version_pattern.match(vms[2].strip())
                                    major = int(vm.group("major")) if vm else -1
                                    minor = int(vm.group("minor")) if vm else -1
                                    build = int(vm.group("build")) if vm else -1
                                    comment = vms[3].strip()
                                    if not major in versions:
                                        versions[major] = {}
                                    if not minor in versions[major]:
                                        versions[major][minor] = {}
                                    # and build is not None:
                                    if build in versions[major][minor]:
                                        old_comment = versions[major][minor][build]["comment"]
                                        versions[major][minor][build]["comment"] = "\n\t\t\t".join(
                                            (old_comment, comment))
                                    else:
                                        #                     elif build is not None:
                                        version_data = {"date": date, "author": author,
                                                        "file": file, "comment": comment, }
                                        versions[major][minor][build] = version_data
                    else:
                        print(f"skipping file: {file}")
                        files_skipped.append(os.path.join(root, file))
        if self.debug:
            for fp in files_processed:
                print(f'TodoReview: processed [{fp}]')
            for fs in files_skipped:
                print(f'TodoReview: skipped[{fs}]')
        return (objects, versions, files_processed, files_skipped)

    def save_changelog_by_object(self, a_objects: dict, a_file_name: str = "changelog_by_object.md") -> None:
        """Convert a dictionary of object version into a changelog file"""

        with open(os.path.join(self.target_path, a_file_name), "w", encoding="utf8") as f:
            f.write("# Changelog by object")
            for object_type, schemas in sorted(a_objects.items()):
                f.write(f"\n\n## {object_type}")
                for schema, objects in sorted(schemas.items()):
                    f.write(f"\n\n### {schema}")
                    for object_name, data in sorted(objects.items()):
                        f.write(f"\n\n#### {object_name}")
                        f.write(f"\nfile: {data['file']}")
                        f.write(f"\nversions:\n{data['versions']}")

    def save_changelog_by_version(self, a_versions: dict, a_file_name: str = "changelog_by_version.md") -> None:
        """Convert a dictionary of version into a changelog file"""

        with open(os.path.join(self.target_path, a_file_name), "w", encoding="utf8") as f:
            f.write("# Changelog by version")
            for major, major_data in sorted(a_versions.items(), reverse=True):
                ma = major if major > -1 else "Major unknown"
                madw = f"\n\n## {ma}"
                f.write(madw)
                for minor, minor_data in sorted(major_data.items(), reverse=True):
                    mi = minor if minor > -1 else "Minor unknown"
                    midw = f"\n\n### {ma}.{mi}\n"
                    f.write(midw)
                    for b, bd in sorted(minor_data.items(), reverse=True):
                        a, c, d, fi = bd["author"], bd["comment"], bd["date"], bd["file"]
                        bi = b if b > -1 else "Build unknown"
                        bdw = f"\n\t{ma.mi.bi} - {c}\t\t(in [{fi}] by {a} at {d})"
                        f.write(bdw)
