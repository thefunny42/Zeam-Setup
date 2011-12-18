
import logging
import os

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import open_uri

logger = logging.getLogger('zeam.setup')


class Template(Recipe):
    """Create files and folder from a given template.
    """

    def __init__(self, options, status):
        super(Template, self).__init__(options, status)
        status.requirements.append('Genshi')

    def prepare(self):
        from genshi.template import NewTextTemplate, MarkupTemplate

        self.formats = {'.template_xml': MarkupTemplate,
                        '.template_text': NewTextTemplate}

    def render_template(self, source_path, output_path, factory):
        __status__ = u"Rendering template %s." % output_path
        logger.info('Creating file %s from template.' % output_path)
        success = False
        source_file = open_uri(source_path)
        try:
            template = factory(source_file.read())
            output_file = open(output_path, 'wb')
            try:
                output_file.write(
                    template.generate(
                        section=self.options,
                        configuration=self.options.configuration
                        ).render())
                success = True
            finally:
                output_file.close()
        finally:
            source_file.close()
        if success:
            os.remove(source_path)
        return output_path

    def render_file(self, filename, prefix=None):
        for format, factory in self.formats.items():
            if filename.endswith(format):
                if prefix:
                    filename = os.path.join(prefix, filename)
                return self.render_template(
                    filename,
                    filename[:-len(format)],
                    factory)

    def render_directory(self, path):
        for prefix, directories, filenames in os.walk(path):
            for filename in filenames:
                self.render_file(filename, prefix)

    def install(self):
        __status__ = u"Installing templates."
        for path in self.status.paths.get_added():
            if os.path.isdir(path):
                self.render_directory(path)
            else:
                assert self.status.paths.rename(path, self.render_file(path))
