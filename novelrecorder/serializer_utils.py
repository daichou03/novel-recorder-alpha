from rest_framework.fields import Field
from rest_framework import serializers

from novelrecorder.models import Description


class ReadOnlyMixin(Field):
    def __new__(cls, *args, **kwargs):
        setattr(
            cls.Meta,
            "read_only_fields",
            [f.name for f in cls.Meta.model._meta.get_fields()],
        )
        return super(ReadOnlyMixin, cls).__new__(cls, *args, **kwargs)


class YDSerializerMixin(object):
    @property
    def safe_errors(self):
        if hasattr(self, '_errors'):
            return self._errors
        else:
            return []


# Need to include pk in the serializer fields in Meta
class SlaveSerializerMixin(object):
    pk = serializers.SerializerMethodField()

    def get_pk(self, obj):
        return obj.pk


# Need to include 'primary_description_title', 'primary_description_content' in the serializer fields in Meta
class PrimaryDescriptionMixin(object):
    # Note: Still need to declare the SerializerMethodField(s) in the descendant.
    def get_primary_description_object(self, obj) -> Description:
        return obj.getPrimaryDescription()

    def get_primary_description_title(self, obj):
        return self.get_primary_description_object(obj).title

    def get_primary_description_content(self, obj):
        return self.get_primary_description_object(obj).content


class PartialUpdateMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs['partial'] = True
        super().__init__(*args, **kwargs)
