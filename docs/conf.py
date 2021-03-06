# -*- coding: utf-8 -*-

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append("../djangofeeds")
sys.path.append("../tests")
import settings
from django.core.management import setup_environ
from django.conf import settings as dsettings
setup_environ(settings)
dsettings.configure()
import djangofeeds
sys.path.append(os.path.join(os.path.dirname(__file__), "_ext"))

# General configuration
# ---------------------

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'djangodocs']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-feeds'
copyright = u'2009, Web Team, Opera Software'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, djangofeeds.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = djangofeeds.__version__

exclude_trees = ['.build']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

html_use_smartypants = True

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

latex_documents = [
  ('index', 'djangofeeds.tex', ur'djangofeeds Documentation',
   ur'Web Team', 'manual'),
]

html_theme = "ADCTheme"
html_theme_path = ["_theme"]
