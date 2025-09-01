# LarpManager - https://larpmanager.com
# Copyright (C) 2025 Scanagatta Mauro
#
# This file is part of LarpManager and is dual-licensed:
#
# 1. Under the terms of the GNU Affero General Public License (AGPL) version 3,
#    as published by the Free Software Foundation. You may use, modify, and
#    distribute this file under those terms.
#
# 2. Under a commercial license, allowing use in closed-source or proprietary
#    environments without the obligations of the AGPL.
#
# If you have obtained this file under the AGPL, and you make it available over
# a network, you must also make the complete source code available under the same license.
#
# For more information or to purchase a commercial license, contact:
# commercial@larpmanager.com
#
# SPDX-License-Identifier: AGPL-3.0-or-later OR Proprietary

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.urls import reverse as django_reverse
import django.urls
import traceback
from django.views.generic.base import TemplateView

import logging
import os

# Define a log file path
LOG_FILE = os.path.join(os.path.dirname(__file__), 'debug.log')

# Configure the logger
logging.basicConfig(
    level=logging.DEBUG,                # Capture all debug/info/warning/error messages
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler()         # optional: still prints to console
    ]
)

logger = logging.getLogger(__name__)

_real_reverse = django_reverse

def reverse(name, *args, **kwargs):
    if name == 'orga_ci_character_inventory_edit':
        logger.debug("\n=== Reverse called for 'orga_ci_character_inventory_edit' ===")
        logger.debug("Args: %s", args)
        logger.debug("Kwargs: %s", kwargs)

        stack_list = traceback.extract_stack(limit=20)
        # Find the first frame outside Django packages
        user_frame = next((f for f in reversed(stack_list) if 'site-packages/django' not in f.filename), None)
        if user_frame:
            logger.debug("First non-Django call: %s:%s in %s", user_frame.filename, user_frame.lineno, user_frame.name)
        else:
            logger.debug("All stack frames are Django internals.")

        # Optionally log full stack if needed
        full_stack = ''.join(traceback.format_list(stack_list))
        logger.debug("Full stack:\n%s", full_stack)

# Override Django's reverse globally
django.urls.reverse = reverse

def redirect_register(request):
    return redirect('/register')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('accounts/register/', redirect_register, name='django_registration_register'),
    path('accounts/', include('django_registration.backends.one_step.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('allauth.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('select2/', include('django_select2.urls')),
    path(
        'robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
    ),
    path('__debug__/', include('debug_toolbar.urls')),
    path('', include('larpmanager.urls')),
]

urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
urlpatterns.extend(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))
