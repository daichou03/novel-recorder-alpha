from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework import fields

from novelrecorder.yd_fields import HiddenInitialContextField, HiddenContextField
from rest_framework.generics import get_object_or_404
from novelrecorder.serializer_utils import ReadOnlyMixin, SlaveSerializerMixin, PrimaryDescriptionMixin, \
    PartialUpdateMixin, YDSerializerMixin

from novelrecorder.models import NovelUser, Novel, Character, NovelUserPermissionModel, Description, Relationship


class YDModelSerializer(serializers.ModelSerializer, YDSerializerMixin):
    pass


# Accounts
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = NovelUser
        fields = ['url', 'username', 'email', 'groups']


class UserRegisterSerializer(YDModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=4,
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        min_length=4,
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    class Meta:
        model = NovelUser
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError('Password don''t match')
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


# Novel Generic serializer
class CustomNovelSerializer(YDModelSerializer):
    fields_to_exclude = []

    class Meta:
        abstract = True

    def currentUser(self):
        return self.context['request'].user

    def getObjectFromGETQueryParamID(self, param_class, param_key_field_name):
        key_value = self.context['request'].GET.get(param_key_field_name)
        if key_value:
            # TODO: 404? Should I always do this here?
            return get_object_or_404(param_class, id=int(key_value)) # Always id for now so convert to int
        else:
            return None

    def validate(self, attrs):
        for field in self.fields_to_exclude:
            if attrs.get(field):
                attrs.pop(field)
        return super().validate(attrs)


# Generic/shared default value
class CustomDefaultField(object):
    def set_context(self, serializer_field):
        # setting field "type", calculated by other serializer fields
        self.request = serializer_field.context['request']


class DefaultFieldCurrentUser(CustomDefaultField):
    def __call__(self):
        return self.request.user


class DefaultFieldCustomFunction(object):
    def __init__(self, value_fn):
        self.value_function = value_fn

    def set_context(self, serializer_field):
        self.value = self.value_function(serializer_field.context)

    def __call__(self):
        return self.value


class FieldQueryParamObject(CustomDefaultField):
    # The 'param_key_field_name' is the 'character_id' in 'description_detail_create/?character_id=3'
    def set_context(self, serializer_field):
        super().set_context(serializer_field)
        self.value = self.request.GET.get(self.param_key_field_name)

    def __init__(self, **kwargs):
        assert 'param_class' in kwargs, 'param_class is a required argument for DefaultFieldData.'
        assert 'param_key_field_name' in kwargs, 'param_key_field_name is a required argument for DefaultFieldData.'
        self.param_class = kwargs['param_class']
        self.param_key_field_name = kwargs['param_key_field_name']

    def __call__(self, **kwargs):
        if hasattr(self, 'value') and self.value: # TODO: Why check if .value exists, i.e. set_context is called? Shouldn't this be asserted and raise error instead if not?
            return get_object_or_404(self.param_class, id=int(self.value)) # Always id for now
        else:
            return None


# Novel
class NovelSerializer(CustomNovelSerializer):
    author = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultFieldCurrentUser()))
    class Meta:
        model = Novel
        fields = ['author', 'name', 'is_public']


class NovelReadOnlySerializer(ReadOnlyMixin, NovelSerializer):
    class Meta:
        model = Novel
        fields = ['author', 'name', 'is_public']


# Description
class DescriptionSerializer(CustomNovelSerializer):
    author = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultFieldCurrentUser()))
    character = HiddenContextField(choices=Character.objects.all(), allow_null=True, required=False)
    relationship = HiddenContextField(choices=Relationship.objects.all(), allow_null=True, required=False)
    content = serializers.CharField(style={'base_template': 'textarea.html'}, allow_blank=True, required=False)

    def validate(self, attrs):
        if not self.partial:
            keys_assigned = 0
            if attrs.get('character'):
                keys_assigned += 1
            if attrs.get('relationship'):
                keys_assigned += 1
            # One and only one these foreign keys should be assigned
            if keys_assigned == 0:
                raise serializers.ValidationError('This description is not linked to either a character or a relationship')
            elif keys_assigned >= 2:
                raise serializers.ValidationError('This description is linked to both character and relationship')
        return super().validate(attrs)

    class Meta:
        model = Description
        fields = ['author', 'character', 'relationship', 'title', 'content']


class DescriptionPartialUpdateSerializer(PartialUpdateMixin, DescriptionSerializer):
    fields_to_exclude = ['author', 'character', 'relationship']

    class Meta:
        model = Description
        fields = ['author', 'character', 'relationship', 'title', 'content']


class DescriptionSlaveSerializer(DescriptionSerializer, SlaveSerializerMixin):
    class Meta:
        model = Description
        fields = ['author', 'character', 'relationship', 'title', 'content', 'pk']


class DescriptionReadOnlySerializer(ReadOnlyMixin, DescriptionSerializer):
    class Meta:
        model = Description
        fields = ['author', 'character', 'relationship', 'title', 'content']


class DescriptionCreateSerializer(DescriptionSerializer):
    character = HiddenInitialContextField(choices=Character.objects.all(),
                                          initial=FieldQueryParamObject(param_class=Character,
                                                                        param_key_field_name='character_id'),
                                          allow_null=True, required=False)
    relationship = HiddenInitialContextField(choices=Relationship.objects.all(),
                                             initial=FieldQueryParamObject(param_class=Relationship,
                                                                           param_key_field_name='relationship_id'),
                                             allow_null=True, required=False)

    class Meta:
        model = Description
        fields = ['author', 'character', 'relationship', 'title', 'content']


# Character
class CharacterSerializer(CustomNovelSerializer):
    class Meta:
        model = Character
        fields = ['name']


class CharacterReadOnlySerializer(ReadOnlyMixin, CharacterSerializer):
    class Meta:
        model = Character
        fields = ['name']


# Lookup primary description. Read only.
class CharacterWithPrimaryDescriptionSerializer(PrimaryDescriptionMixin, CharacterReadOnlySerializer):
    primary_description_title = serializers.SerializerMethodField()
    primary_description_content = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = ['name', 'primary_description_title', 'primary_description_content']


class CharacterWithPrimaryDescriptionSlaveSerializer(CharacterWithPrimaryDescriptionSerializer, SlaveSerializerMixin):
    class Meta:
        model = Character
        fields = ['name', 'primary_description_title', 'primary_description_content', 'pk']


class CharacterCreateSerializer(CharacterSerializer):
    # Also creates a description which is the primary description
    novel = HiddenInitialContextField(choices=Novel.objects.all(),
                                      initial=FieldQueryParamObject(param_class=Novel,
                                                                    param_key_field_name='novel_id'))
    des_title = serializers.CharField(label='Primary Description Title')
    des_content = serializers.CharField(style={'base_template': 'textarea.html'}, label='Primary Description Content', allow_blank=True)

    class Meta:
        model = Character
        fields = ['name', 'novel', 'des_title', 'des_content']

    def create(self, validated_data):
        # TODO: Hmm, either find a better way of doing this or somewhat centralise this logic.
        des_title = validated_data.pop('des_title')
        des_content = validated_data.pop('des_content')
        character = Character.objects.create(**validated_data)
        # This works but is not good because:
        # 1. No serializers for Description so I am directly manipulating model fields
        # 2. Because of #1 I have to specify every single model field where necessary without being able to reuse/take advantage of any Description's serializers. Which means I would likely to repeat myself.
        # However afaik I may have to do this as long as I am doing this for html template form rendering - nested serializer won't do - at least if I want these detail fields to be writable.
        Description.objects.create(author=self.currentUser(), character=character, title=des_title, content=des_content)
        return character


# Relationship
class RelationshipSerializer(CustomNovelSerializer):
    character1 = HiddenContextField(choices=Character.objects.all())
    character2 = HiddenContextField(choices=Character.objects.all())

    class Meta:
        model = Relationship
        fields = ['character1', 'character2']


class RelationshipPartialUpdateSerializer(PartialUpdateMixin, RelationshipSerializer):
    fields_to_exclude = ['character1', 'character2']

    class Meta:
        model = Relationship
        fields = ['character1', 'character2']


class RelationshipReadOnlySerializer(ReadOnlyMixin, RelationshipSerializer):
    class Meta:
        model = Relationship
        fields = ['character1', 'character2']


# Lookup primary description. Read only.
class RelationshipWithPrimaryDescriptionSerializer(PrimaryDescriptionMixin, RelationshipReadOnlySerializer):
    primary_description_title = serializers.SerializerMethodField()
    primary_description_content = serializers.SerializerMethodField()
    character2_id = serializers.SerializerMethodField()
    character2_name = serializers.SerializerMethodField()
    relationship_display = serializers.SerializerMethodField()

    class Meta:
        model = Relationship
        fields = ['character2', 'relationship_display', 'character2_id', 'character2_name', 'primary_description_title', 'primary_description_content']

    def get_character2_id(self, obj: Relationship):
        return obj.character2.id

    def get_character2_name(self, obj: Relationship):
        return obj.character2.name

    def get_relationship_display(self, obj: Relationship):
        return obj.__str__()


class RelationshipWithPrimaryDescriptionSlaveSerializer(RelationshipWithPrimaryDescriptionSerializer, SlaveSerializerMixin):
    class Meta:
        model = Relationship
        fields = ['character2', 'relationship_display', 'character2_id', 'character2_name', 'primary_description_title', 'primary_description_content', 'pk']


class RelationshipCreateSerializer(RelationshipSerializer):
    # Also creates a description which is the primary description
    # TODO: When 1st time makemigrations (deploy), this will complain as Character doesn't exist by now.
    character1 = HiddenInitialContextField(choices=Character.objects.all(), label='Subject Character',
                                      initial=FieldQueryParamObject(param_class=Character,
                                                                    param_key_field_name='character1_id'))
    character2 = HiddenInitialContextField(choices=Character.objects.all(), label='Object Character',
                                      initial=FieldQueryParamObject(param_class=Character,
                                                                    param_key_field_name='character2_id'))
    des_title = serializers.CharField(label='Primary Description Title')
    des_content = serializers.CharField(style={'base_template': 'textarea.html'}, label='Primary Description Content', allow_blank=True)

    class Meta:
        model = Character
        fields = ['character1', 'character2', 'des_title', 'des_content']

    def create(self, validated_data):
        des_title = validated_data.pop('des_title')
        des_content = validated_data.pop('des_content')
        relationship = Relationship.objects.create(**validated_data)
        # Don't think this is ideal, see comments in CharacterCreateSerializer.create.
        Description.objects.create(author=self.currentUser(), relationship=relationship, title=des_title, content=des_content)
        return relationship


# NovelUserPermission
class NovelUserPermissionModelSerializer(CustomNovelSerializer):
    class Meta:
        model = NovelUserPermissionModel
        fields = ['novel', 'user', 'permission']
