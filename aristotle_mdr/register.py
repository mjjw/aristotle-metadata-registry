from __future__ import absolute_import
"""
Aristotle-MDR concept register

This module allows developers to easily register new concept models with the core
functionality of Aristotle-MDR. The ``register_concept`` is a wrapper around three
methods that registers a new concept with the Django-Admin site, with the
Django-Autocomplete and with a class for a Haystack search index. This is all done
in a way that conforms to the permissions required for control item visibility.

Other methods in this module can be called, to highly customise how concepts are
used within the admin site and search, but should be considered internal methods
and future releases of Aristotle-MDR may break code that uses these methods.
"""

import autocomplete_light

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr import autocomplete_light_registry as reg
from aristotle_mdr.search_indexes import conceptIndex

import aristotle_mdr.search_indexes as search_index

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack import indexes

import logging
logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)

def register_concept(concept_class, *args, **kwargs):
    """ .. py:function:: register_concept(concept_class, *args, **kwargs)

    A handler for third-party apps to make registering
    extension models based on ``aristotle_mdr.models.concept`` easier.

    Sets up the search index, django administrator page and autocomplete handlers.
    All ``args`` and ``kwargs`` are passed to the called methods. For examples of
    what can be passed into this method review the other methods in
    ``aristotle_mdr.register``.

    Example usage (based on the models in the extensions test suite):

        register_concept(Question, extra_fieldsets=[('Question','question_text'),]
    """
    register_concept_autocomplete(concept_class, *args, **kwargs)
    register_concept_admin(concept_class, *args, **kwargs)
    register_concept_search_index(concept_class, *args, **kwargs)

def register_concept_autocomplete(concept_class, *args, **kwargs):
    """ .. py:function:: register_concept_autocomplete(concept_class, *args, **kwargs)

    Registers the given ``concept`` with ``autocomplete_light`` based on the
    in-built ``aristotle_mdr.autocomplete_light_registry.PermissionsAutocomplete``.
    This ensures the autocomplete for the registered conforms to Aristotle permissions.

    :param concept concept_class: The model that is to be registered
    """
    x = reg.autocompleteTemplate.copy()
    x['name']='Autocomplete'+concept_class.__name__
    autocomplete_light.register(concept_class,reg.PermissionsAutocomplete,**x)

def register_concept_search_index(concept_class, *args, **kwargs):
    """ .. py:function:: register_concept_search_index(concept_class, *args, **kwargs)

    Registers the given ``concept`` with a Haystack search index that conforms
    to Aristotle permissions. If the concept to be registered does not have a
    template for serving a search document, a basic document with just the basic
    fields from ``aristotle_mdr.models._concept`` will be used when indexing items.

    :param concept concept_class: The model that is to be registered for searching.
    """
    class_name = "%s_%sSearchIndex"%(concept_class._meta.app_label,concept_class.__name__)
    setattr(search_index, class_name, create(concept_class))

    # Since we've added a new class, kill the index so it is rebuilt.
    connections[DEFAULT_ALIAS]._index = None

def create(cls):
    class SubclassedConceptIndex(conceptIndex, indexes.Indexable):
        def get_model(self):
            return cls
    return SubclassedConceptIndex


def register_concept_admin(concept_class, *args, **kwargs):
    """ .. py:function:: register_concept_admin(concept_class, *args, **kwargs)

    Registers the given ``concept`` with the Django admin backend based on the default
    ``aristotle_mdr.admin.ConceptAdmin``.

    Additional parameters are only required if a model has additional fields or
    references to other models.

    :param boolean auto_fieldsets: If no extra_fieldsets, when set to true this generates a list of fields for the admin page as "Extra fields for [class]"
    :param concept concept_class: The model that is to be registered
    :param list extra_fieldsets: Model-specific `fieldsets <https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.admin.ModelAdmin.fieldsets>`_ to be displayed. Fields in the tuples given should be those *not* defined by the base ``aristotle_mdr.models._concept``class.
    :param list extra_inlines: Model-specific `inline <https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.admin.ModelAdmin.inlines>`_ admin forms to be displayed.
    """
    extra_fieldsets = kwargs.get('extra_fieldsets',[])
    auto_fieldsets = kwargs.get('auto_fieldsets',False)
    extra_inlines = kwargs.get('extra_inlines',[])
    extra_name_suggest_fields = kwargs.get('name_suggest_fields',[])

    # late import this as we call this in aristotle_mdr.admin and need it to be ready before we call this.
    from aristotle_mdr.admin import ConceptAdmin

    if not extra_fieldsets and auto_fieldsets:
        handled_fields = [ x
            for name, k in ConceptAdmin.fieldsets
                for x in k.get('fields',[]) ]

        auto_fieldset = [f.name for f in concept_class._meta.fields if f.name not in handled_fields]

        extra_fieldsets_name = _('Extra fields for %(class_name)s') %{'class_name':concept_class._meta.verbose_name.title()}
        extra_fieldsets = [(extra_fieldsets_name, {'fields': auto_fieldset}),]

    class SubclassedConceptAdmin(ConceptAdmin):
        model = concept_class
        if extra_name_suggest_fields:
            name_suggest_fields = extra_name_suggest_fields
        fieldsets = ConceptAdmin.fieldsets + extra_fieldsets
        inlines = ConceptAdmin.inlines + extra_inlines

    admin.site.register(concept_class,SubclassedConceptAdmin)

#def _register_concept_(concept_class, *args, **kwargs):
#    pass
