#!/usr/bin/env python3
#coding:utf-8
"""
  Author:  gemisigo --<gemisigo@gmail.com>
  Purpose: helper functions
  Created: 2022-05-28 12:48:40
"""

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

