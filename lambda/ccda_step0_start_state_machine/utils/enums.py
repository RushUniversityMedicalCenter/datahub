'''
File: enums.py
Project: utils
File Created: Monday, 21st December 2020 11:19:23 am
Author: Canivel, Danilo (dccanive@amazon.com)
Description: That is the Enums ... ;)
-----
Last Modified: Tuesday, 22nd December 2020 8:41:30 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

from enum import Enum


class Status(Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE = 'COMPLETE'
    FAIL = 'FAIL'


class Key(Enum):
    CONSUMPTION_COUNT = 'consumption_count'
    ITEM = 'Item'
    MESSAGE_ID = 'messageId'
    RECORDS = 'Records'
    STATUS = 'status'
    UPDATED = 'updated'
