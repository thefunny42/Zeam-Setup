
import logging
import os
import shutil

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import open_uri
from zeam.setup.base.error import InstallationError

logger = logging.getLogger('zeam.setup')


class TemplateRenderingError(InstallationError):
    """Error while rendering the template.
    """
    name = u'Error while rendering the template'

    def __init__(self, error):
        message = ''
        if error.lineno >= 1:
            message = 'line %d: ' % (error.lineno)
        if error.offset >= 0:
            message += 'column %d: ' % (error.offset)
        message += error.msg
        super(TemplateRenderingError, self).__init__(message)


class Template(Recipe):
    """Create files and folder from a given template.
    """

    def __init__(self, options, status):
        super(Template, self).__init__(options, status)
        status.requirements.append('Genshi')

    def preinstall(self):
        from genshi.template import NewTextTemplate, MarkupTemplate

        self.formats = {'.template_xml': MarkupTemplate,
                        '.template_text': NewTextTemplate}

    def render_template(self, source_path, output_path, factory):
        __status__ = u"Rendering template for %s." % output_path
        from genshi.template import TemplateError

        logger.info('Creating file %s from template.' % output_path)
        success = False
        source_file = open_uri(source_path)
        try:
            try:
                template = factory(source_file.read())
            except TemplateError, error:
                raise TemplateRenderingError(error)
            output_file = open(output_path, 'wb')
            try:
                output_file.write(
                    template.generate(
                        section=self.options,
                        configuration=self.options.configuration,
                        status=self.status
                        ).render())
                success = True
            except TemplateError, error:
                raise TemplateRenderingError(error)
            finally:
                output_file.close()
        finally:
            source_file.close()
        if success:
            shutil.copystat(source_path, output_path)
            assert self.status.paths.rename(source_path, output_path)
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
        for path in self.status.paths.query(added=True):
            if os.path.isdir(path):
                self.render_directory(path)
            else:
                self.render_file(path)
