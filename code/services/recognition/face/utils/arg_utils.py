# -*- coding:UTF-8 -*-
"""
@create: 2021-10-06 10:50:00
@author: GongChen
@description: 从args.yml文件中获取参数
"""

import yaml


def fetch_args():
    yaml_path = 'args.yml'
    with open(yaml_path, 'r', encoding='utf-8') as f:
        args = f.read()
        args = yaml.load(args)
        return args