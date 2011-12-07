
import logging
import os

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import open_uri

logger = logging.getLogger('zeam.setup')


class Template(Recipe):
    """Create files and folder from a given template.
    """
    requirements = ['Genshi']

    def render(self, source_path, output_path, factory):
        logger.info('Creating file %s.' % output_path)
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

    def install(self, status):
        __status__ = u"Installing templates."
        from genshi.template import NewTextTemplate, MarkupTemplate

        available_formats = {'.template_xml': MarkupTemplate,
                             '.template_text': NewTextTemplate}

        for base_path in status.paths:
            for path, directories, filenames in os.walk(base_path):
                for filename in filenames:
                    for format, factory in available_formats.items():
                        if filename.endswith(format):
                            self.render(
                                os.path.join(path, filename),
                                os.path.join(path, filename[:-len(format)]),
                                factory)
