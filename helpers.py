#!/usr/bin/env python3
#coding:utf-8
"""
  Author:  gemisigo --<gemisigo@gmail.com>
  Purpose: helper functions
  Created: 2022-05-28 12:48:40
"""

import os
import sublime
import sublime_plugin
import time
import subprocess

from TodoReview.tabulate import tabulate
from typing import Union


def print_table(a_table: Union[list, tuple], a_header: tuple, a_table_fmt: str = "psql"):
    """Function that prints the provided list and header in table format"""

#     if not isinstance(a_table, Union[list[list], list[tuple], tuple[list], tuple[tuple]]) and isinstance(a_table, Union[list[str], tuple[str]]):
    if isinstance(a_table, Union[list, tuple]) and not isinstance(a_table[0], Union[list, tuple]):
        table = [(r,) for r in a_table]
    else:
        table = a_table
    print(tabulate(table, a_header, tablefmt=a_table_fmt))


def run_cli(app, args, target, stdin=None, timeout=5, cwd=None):
    # run cli commands, return stdout, returncode
    cmd = [app] + args + [target]
    try:
      # Hide popups on Windows
      si = None
      if sublime.platform() == "windows":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

      start = time.time()
      p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy(), startupinfo=si, cwd=cwd)
      stdout, stderr = p.communicate(input=stdin, timeout=timeout)
      p.wait(timeout=timeout)
      elapsed = round(time.time() - start)
      print("process {0} returned ({1}) in {2} seconds".format(app, str(p.returncode), str(elapsed)))
      stderr = stderr.decode("utf-8")
      if len(stderr) > 0:
        print("stderr:\n{0}".format(stderr))
      return stdout.decode("utf-8"), p.returncode

    except:
      sublime.error_message('Error happens when run: ' + app + ', check the console')
      print("$ args: ", args)
      print("$ target: " + target)
