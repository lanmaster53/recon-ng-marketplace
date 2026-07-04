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
# permute.py references this module-level constant from inside its meta block
# (options default). The index never reads `options`, so any value works — it
# just has to be a defined name so exec() of the meta dict doesn't NameError.
DEFAULT_WORDS = []

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
        lines = []
        for line in fp:
            if line == begin:
                state = True
            if state:
                lines.append(line.strip())
            if line == end and state == True:
                break
    # Join with newlines (not bare concatenation) so a full-line `#` comment
    # inside the meta block stays a comment instead of swallowing the rest of
    # the dict on the same logical line.
    return '\n'.join(lines) or 'meta = {}'

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
    # Append modules that exist on disk but aren't in the old index yet —
    # without this, newly added modules are silently never indexed.
    old_keys = {item_old[key] for item_old in old}
    for item_new in new:
        if item_new[key] not in old_keys:
            print(f"New module indexed: {item_new[key]}.")
            item_new['last_updated'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
            modules.append(item_new)
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
