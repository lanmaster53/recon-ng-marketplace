#!/usr/bin/env python3

##### BEGIN DUMMY OBJECTS #####

import hashlib

class BaseModule(object):

    workspace = ''
    data_path = ''

def _build_options(*args, **kwargs):

    return []

ghdb = None
patterns = {}

##### END DUMMY OBJECTS #####

from datetime import datetime
import os
import yaml

def get_module_paths():
    # crawl the module directory and build the module list
    modules = []
    for dirpath, dirnames, filenames in os.walk('modules', followlinks=True):
        # remove hidden files and directories
        filenames = [f for f in filenames if not f[0] == '.']
        dirnames[:] = [d for d in dirnames if not d[0] == '.']
        if len(filenames) > 0:
            # only analyze python files
            for filename in [f for f in filenames if f.endswith('.py')]:
                modules.append(os.path.join(dirpath, filename))
    return modules

def parse_meta(filepath):
    begin = '    meta = {\n'
    end = '    }\n'
    with open(filepath) as fp:
        state = False
        meta_src = ''
        for line in fp:
            if line == begin:
                state = True
            if state:
                meta_src += line.strip()
            if line == end and state == True:
                break
    return meta_src or 'meta = {}'

def build_new_modules_for_yaml():
    module_paths = get_module_paths()
    modules = []
    for module_path in sorted(module_paths):
        # parse the meta object from the module
        exec(parse_meta(module_path), globals())
        # build a yaml object for the module
        module = {}
        # not in meta
        module['path'] = os.path.sep.join(module_path.split(os.path.sep)[1:])[:-3]
        # module['last_updated'] added later if changes are detected
        # meta required
        module['author'] = meta.get('author')
        module['name'] = meta.get('name')
        module['description'] = meta.get('description')
        module['version'] = meta.get('version', '1.0')
        # meta optional
        module['dependencies'] = meta.get('dependencies', [])
        module['files'] = meta.get('files', [])
        module['required_keys'] = meta.get('required_keys', [])
        modules.append(module)
    return modules

def get_old_modules_from_yaml():
    with open('modules.yml') as infile:
        modules = yaml.load(infile, Loader=yaml.FullLoader)
    return modules

def merge_lists_of_modules(old, new, key='path'):
    modules = []
    for item_old in old:
        updated = False
        for item_new in new:
            if item_old[key] == item_new[key]:
                item_new['last_updated'] = item_old['last_updated']
                if item_old != item_new:
                    print(f"Changes detected in {item_old[key]}.")
                    item_new['last_updated'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
                    modules.append({**item_old, **item_new})
                    updated = True
                break
        if not updated:
            modules.append(item_old)
    return modules

def main():
    old_modules = get_old_modules_from_yaml()
    new_modules = build_new_modules_for_yaml()
    modules = merge_lists_of_modules(old_modules, new_modules)
    markup = yaml.safe_dump(modules)
    with open('modules.yml', 'w') as outfile:
        outfile.write(markup)
    print('Module index created.')
    print(f"{len(modules)} modules indexed.")

if __name__ == "__main__":
    # execute only if run as a script
    main()
