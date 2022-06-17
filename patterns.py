#!/usr/bin/env python3
#coding:utf-8
"""
  Author:  gemisigo --<gemisigo@gmail.com>
  Purpose: contain the regular expression patterns required to collect objects and versions
  Created: 2022-05-28 12:30:29
"""

import re
from TodoReview.types import TYPES

VERSION_LIST_PATTERN = "(?:-- #region\s*\**\sversions start\s*\**?\n)(?P<versions>.*?)(?:-- #endregion\s*\**\sversions end\s*\**)"
VERSION_ENTRY_PATTERN = "^-- (?P<date>.{20})\s*(?P<author>\w*)\s* - \((?P<version>.*?)\)\s+(?P<comment>.*)$"
VERSION_PATTERN = "^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<build>\d+)$"
# OBJECT_PATTERN = f"^(?P<type>{'|'.join(TYPES.keys())})\.(?P<schema>.*?)\.(?P<object>.*?)\.sql$"
OBJECT_PATTERN = f"^(?P<rubbish>.*?)(?P<type>{'|'.join(TYPES.keys())})\.(?P<schema>.*?)\.(?P<object>.*?)\.sql$"

object_pattern = re.compile(OBJECT_PATTERN) # , re.DOTALL | re.MULTILINE)
version_list_pattern = re.compile(VERSION_LIST_PATTERN, re.DOTALL | re.MULTILINE)
version_entry_pattern = re.compile(VERSION_ENTRY_PATTERN, re.MULTILINE)
version_pattern = re.compile(VERSION_PATTERN)
