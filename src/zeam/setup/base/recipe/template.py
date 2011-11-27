
import os

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri, create_directory


class Template(Recipe):
    """Create files and folder from a given template.
    """
    requirements = ['Genshi']

    def __init__(self, configuration):
        super(Template, self).__init__(configuration)
        self.templates = configuration['templates'].as_list()
        self.format = configuration.get('format', 'text').as_text()

    def install(self):
        __status__ = u"Installing templates."
        from genshi.template import NewTextTemplate, MarkupTemplate

        available_formats = {'xml': MarkupTemplate, 'text': NewTextTemplate}
        created_templates = []

        if self.format not in available_formats:
            raise ConfigurationError(
                u"Unknown template format", self.format)
        for paths in self.templates:
            parts = paths.split()
            if len(parts) != 2:
                raise ConfigurationError(
                    u"Invalid template definition line", paths)
            source_file = open_uri(parts[0])
            try:
                template = available_formats[self.format](source_file.read())
                create_directory(os.path.basename(parts[1]))
                output_file = open(parts[1], 'wb')
                try:
                    output_file.write(
                        template.generate(
                            section=self.configuration,
                            configuration=self.configuration.configuration
                            ).render())
                    created_templates.append(parts[1])
                finally:
                    output_file.close()
            finally:
                source_file.close()
        return created_templates
