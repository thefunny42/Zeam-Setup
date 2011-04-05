
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.archives import ARCHIVE_MANAGERS


class Template(Recipe):
    """Create files and folder from a given template.
    """
    requirements = ['Genshi']

    def __init__(self, configuration):
        super(Template, self).__init__(configuration)
        self.templates = configuration['templates'].as_list()

    def install(self):
        for template in self.templates:
            pass
