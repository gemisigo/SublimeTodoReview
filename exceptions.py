#!/usr/bin/env python3
#coding:utf-8
"""
  Author:  gemisigo --<gemisigo@gmail.com>
  Purpose: exceptions
  Created: 2022-05-28 12:32:56
"""


class VersionError(Exception):
    """Base Version Error class for storing versions in a dictionary"""
    error_code = -1
    reason = "Base Version Error"


class BuildExistsError(VersionError):
    """Raised when a build already exists in the versions dictionary"""
    error_code = -2
    reason = "Build [{build}] already exists in the versions dictionary"

    def __init__(self, a_build: int):
        self.reason = self.reason.format(build=a_build)

