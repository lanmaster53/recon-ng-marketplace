from recon.core.module import BaseModule
import codecs
import os
import re
import time
import webbrowser

class Module(BaseModule):

    meta = {
        'name': 'PushPin Report Generator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Creates HTML media and map reports for all of the PushPins stored in the database.',
        'required_keys': ['google_api'],
        'options': (
            ('latitude', None, True, 'latitude of the epicenter'),
            ('longitude', None, True, 'longitude of the epicenter'),
            ('radius', None, True, 'radius from the epicenter in kilometers'),
            ('map_filename', os.path.join(BaseModule.workspace, 'pushpin_map.html'), True, 'path and filename for PushPin map report'),
            ('media_filename', os.path.join(BaseModule.workspace, 'pushpin_media.html'), True, 'path and filename for PushPin media report'),
        ),
        'files': ['template_media.html', 'template_map.html'],
    }

    def remove_nl(self, x, repl=''):
        return re.sub('[\r\n]+', repl, self.html_escape(x))

    def build_content(self, sources):
        icons = {
            'flickr': 'http://maps.google.com/mapfiles/ms/icons/orange-dot.png',
            'instagram': 'http://maps.google.com/mapfiles/ms/icons/pink-dot.png',
            'picasa': 'http://maps.google.com/mapfiles/ms/icons/purple-dot.png',
            'shodan': 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
            'twitter': 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
            'youtube': 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
        }

        media_content = ''
        map_content = ''
        map_arrays = ''
        map_checkboxes = ''
        for source in sources:
            count = source[0]
            source = source[1]
            map_arrays += f"var {source.lower()} = [];\n"
            map_checkboxes += f'<input type="checkbox" id="{source.lower()}" onchange="toggleMarkers(\'{source.lower()}\');" checked="checked"/>{source}<br />\n'
            media_content += f'<div class="media_column {source.lower()}">\n<div class="media_header"><div class="media_summary">{count}</div>{source.capitalize()}</div>\n'
            items = self.query('SELECT * FROM pushpins WHERE source=?', (source,))
            items.sort(key=lambda x: x[9], reverse=True)
            for item in items:
                item = [self.to_unicode_str(x) if x != None else '' for x in item]
                media_content += f'<div class="media_row"><div class="prof_cell"><a href="{item[4]}" target="_blank"><img class="prof_img rounded" src="{item[5]}" /></a></div><div class="data_cell"><div class="trigger" id="trigger" lat="{item[7]}" lon="{item[8]}">[<a href="{item[3]}" target="_blank">{item[2]}</a>] {self.remove_nl(item[6], "<br />")}<br /><span class="time">{item[9]}</span></div></div></div>\n'
                map_details = (f"<table><tr><td class='prof_cell'><a href='{item[4]}' target='_blank'><img class='prof_img rounded' src='{item[5]}' /></a></td><td class='data_cell'>[<a href='{item[3]}' target='_blank'>{self.remove_nl(item[2])}</a>] {self.remove_nl(item[6], '<br />')}<br /><span class='time'>{item[9]}</span></td></tr></table>")
                map_content += f'add_marker({{position: new google.maps.LatLng({item[7]},{item[8]}),title:"{self.remove_nl(item[2])}",icon:"{icons[source.lower()]}",map:map}},{{details:"{map_details}"}}, "{source.lower()}");\n'
            media_content += '</div>\n'
        return (media_content,), (map_content, map_arrays, map_checkboxes)

    def write_markup(self, template, filename, content):
        temp_content = open(template).read()
        page = temp_content % content
        with codecs.open(filename, 'wb', 'utf-8') as fp:
            fp.write(page)

    def module_run(self):
        key = self.keys.get('google_api')
        sources = self.query('SELECT COUNT(source), source FROM pushpins GROUP BY source')
        media_content, map_content = self.build_content(sources)
        meta_content = (self.options['latitude'], self.options['longitude'], self.options['radius'])
        # create the media report
        media_content = meta_content + media_content
        media_filename = self.options['media_filename']
        self.write_markup(os.path.join(self.data_path, 'template_media.html'), media_filename, media_content)
        self.output(f"Media data written to '{media_filename}'")
        # order the map_content tuple
        map_content = meta_content + map_content + (key,)
        order = [6, 4, 0, 1, 2, 3, 5]
        map_content = tuple([map_content[i] for i in order])
        # create the map report
        map_filename = self.options['map_filename']
        self.write_markup(os.path.join(self.data_path, 'template_map.html'), map_filename, map_content)
        self.output(f"Mapping data written to '{map_filename}'")
        # open the reports in a browser
        w = webbrowser.get()
        w.open(media_filename)
        time.sleep(2)
        w.open(map_filename)
