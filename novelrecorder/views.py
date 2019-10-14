from django.http import Http404
from rest_framework import status, serializers
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect

from django.shortcuts import get_object_or_404
import django.urls
from django.views.generic import ListView
from rest_framework import generics
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from novelrecorder.models import NovelUser, Relationship
from novelrecorder.models import Novel
from novelrecorder.models import Character
from novelrecorder.models import Description
import novelrecorder.permissions
from novelrecorder.serializers import NovelSerializer, NovelReadOnlySerializer, \
    CharacterSerializer, CharacterReadOnlySerializer, CharacterWithPrimaryDescriptionSerializer, DescriptionSerializer, \
    DescriptionReadOnlySerializer, DescriptionCreateSerializer, CharacterCreateSerializer, \
    CharacterWithPrimaryDescriptionSlaveSerializer, DescriptionSlaveSerializer, RelationshipSerializer, \
    RelationshipReadOnlySerializer, RelationshipWithPrimaryDescriptionSerializer, RelationshipCreateSerializer, \
    RelationshipWithPrimaryDescriptionSlaveSerializer, UserRegisterSerializer, DescriptionPartialUpdateSerializer, \
    RelationshipPartialUpdateSerializer

from novelrecorder.yd_exceptions import DataErrorException


# Generic
class CustomHTMLViewMixin(object):
    renderer_classes = [TemplateHTMLRenderer]
    style = {'template_pack': 'rest_framework/vertical/'}

    def get_queryset(self):
        return self.model_class.objects.all()


class CustomNovelMixin(CustomHTMLViewMixin):
    permission_classes = [novelrecorder.permissions.NovelUserPermission]
    _model_class = None
    _data_name_single = ''
    _data_name_plural = ''
    _writable_serializer = None
    _read_only_serializer = None

    def get_model_class(self):
        assert self._model_class, 'Class %s._model_class is not set.' % self.__class__.__name__
        return self._model_class

    def get_data_name_single(self):
        assert self._data_name_single != '', 'Class %s._data_name_single is not set.' % self.__class__.__name__
        return self._data_name_single

    def get_data_name_plural(self):
        assert self._data_name_plural != '', 'Class %s._data_name_plural is not set.' % self.__class__.__name__
        return self._data_name_plural

    def get_writable_serializer(self):
        assert self._writable_serializer, 'Class %s._writable_serializer is not set.' % self.__class__.__name__
        return self._writable_serializer

    def get_read_only_serializer(self):
        assert self._read_only_serializer, 'Class %s._read_only_serializer is not set.' % self.__class__.__name__
        return self._read_only_serializer

    def has_write_permission(self):
        return True

    def get_serializer_class(self):
        if self.has_write_permission():
            return self.get_writable_serializer()
        else:
            return self.get_read_only_serializer()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'has_write_permission': self.has_write_permission()})
        return context

    model_class = property(get_model_class)
    data_name_single = property(get_data_name_single)
    data_name_plural = property(get_data_name_plural)
    read_only_serializer = property(get_read_only_serializer)
    writable_serializer = property(get_writable_serializer)


class CustomNovelRetrieveMixin(CustomNovelMixin):
    def get(self, request, pk):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'serializer': serializer, self.data_name_single: instance})


class CustomNovelListMixin(CustomNovelMixin):
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        return Response({'serializer': serializer, self.data_name_plural: self.get_queryset})


# Basically post and delete.
class CustomHTMLRedirectMixin(CustomHTMLViewMixin):
    url_to_redirect_reverse = ''

    # Override this if needs a custom redirect method other than just assigning url_to_redirect_reverse
    def on_redirect(self, serializer):
        return None

    def default_redirect(self, serializer):
        raise NotImplementedError('The class %s does not implement default_redirect() as a descendant of CustomHTMLRedirectMixin.') % self.__class__.__name__

    def do_redirect(self, serializer):
        custom_redirect = self.on_redirect(serializer)
        if custom_redirect:
            return custom_redirect
        elif self.url_to_redirect_reverse:
            return redirect(django.urls.reverse_lazy(self.url_to_redirect_reverse))
        else:
            return self.default_redirect(serializer)


class CustomHTMLUpdateMixin(CustomHTMLRedirectMixin):
    def default_redirect(self, serializer):
        return Response({'serializer': serializer, self.data_name_single: self.get_object()})

    def post(self, request, pk):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if not serializer.is_valid():
            return Response({'serializer': serializer, self.data_name_single: instance})
        serializer.save()
        return self.do_redirect(serializer)


class CustomHTMLCreateMixin(CustomHTMLRedirectMixin):
    def get(self, request):
        serializer = self.get_serializer()
        return Response({'serializer': serializer, 'style': self.style})

    def default_redirect(self, serializer):
        return Response({'serializer': serializer}, status=status.HTTP_201_CREATED)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return self.do_redirect(serializer)
        else:
            return Response({'serializer': serializer}, status=status.HTTP_400_BAD_REQUEST)


class CustomHTMLDeleteMixin(CustomHTMLRedirectMixin):
    def default_redirect(self, serializer): # TODO: Don't think would work as clashing with Update too, need to do something. But does it need one?
        return Response({'serializer': serializer}, status=status.HTTP_204_NO_CONTENT)

    # For validation and raise validation exception here
    def pre_delete(self, serializer):
        return True

    # Delete
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        try:
            self.pre_delete(serializer)
        except Exception as e:
            return self.do_redirect(serializer) # TODO: redirect back without any error message for now.
        super().delete(self, request)
        return self.do_redirect(serializer)


class CustomNovelUpdateMixin(CustomNovelMixin, CustomHTMLUpdateMixin):
    pass


class CustomNovelCreateMixin(CustomNovelMixin, CustomHTMLCreateMixin):
    pass


class CustomNovelDeleteMixin(CustomNovelMixin, CustomHTMLDeleteMixin):
    pass


class CustomNovelRUDDetailView(CustomNovelRetrieveMixin, CustomNovelUpdateMixin, CustomNovelDeleteMixin, generics.RetrieveUpdateDestroyAPIView):
    class Meta:
        abstract = True

    def has_write_permission(self):
        for permission in self.permission_classes:
            permissionObj = permission()
            if isinstance(permissionObj, novelrecorder.permissions.NovelUserPermission):
                if not permission.custom_has_object_permission(permissionObj, self.request.user, True, self.get_object()):
                    return False
        return True

    def get_queryset(self):
        return self.model_class.objects.all()


class CustomNovelListCreateView(CustomNovelListMixin, generics.ListCreateAPIView):
    query_param_names = [] # The query param names need to be passed to the GET request for the create page

    class Meta:
        abstract = True

    def get_filter_object(self):
        raise NotImplementedError('Class %s.get_filter_object is not implemented.' % self.__class__.__name__)

    def has_write_permission(self):
        for permission in self.permission_classes:
            permissionObj = permission()
            if isinstance(permissionObj, novelrecorder.permissions.NovelUserPermission):
                if not permission.custom_has_object_permission(permissionObj, self.request.user, True, self.get_filter_object()):
                    return False
        return True

    def get_queryset(self):
        raise NotImplementedError('Class %s.get_queryset is not implemented.' % self.__class__.__name__)

    def get_serializer_context(self):
        context = super(CustomNovelListCreateView, self).get_serializer_context()
        for param_name in self.query_param_names:
            context.update({
                param_name: self.kwargs[param_name]
            })
        return context


@method_decorator(login_required, name='dispatch')
class CustomNovelCreateView(CustomNovelCreateMixin, generics.CreateAPIView):
    # Note that _read_only_serializer shouldn't be reached, but overriding it here won't do as in the multiple inheritance this comes after the "Model"Mixins.
    class Meta:
        abstract = True


@method_decorator(login_required, name='dispatch')
class CustomNovelDeleteView(CustomNovelDeleteMixin, generics.DestroyAPIView):
    class Meta:
        abstract = True


# Accounts
class UserRegisterView(CustomHTMLCreateMixin, generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    template_name = 'registration/register.html'
    url_to_redirect_reverse = 'login'


# Index
def index(request):
    # Generate dynamic contents
    num_novels = Novel.objects.all().count()
    num_characters = Character.objects.all().count()
    num_descriptions = Description.objects.count()
    num_relationships = Relationship.objects.count()
    num_authors = NovelUser.objects.all().count()  # TODO: Return num of users who owns at least 1 novel only.

    context = {
        'num_novels': num_novels,
        'num_characters': num_characters,
        'num_descriptions': num_descriptions,
        'num_authors': num_authors,
        'num_relationships': num_relationships,
    }

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)


def redirect_novelRecorder(request):
    response = redirect(django.urls.reverse_lazy('novelrecorder:index'))
    return response


class PublicNovelListView(ListView):
    template_name = 'novelrecorder/public_novel_list.html'
    context_object_name = 'public_novel_list'

    def get_queryset(self):
        return Novel.objects.filter(is_public=True)


# Novel
class NovelViewMixin(object):
    _model_class = Novel
    _writable_serializer = NovelSerializer
    _read_only_serializer = NovelReadOnlySerializer
    _data_name_single = 'novel'
    _data_name_plural = 'novels'


class NovelDetailView(NovelViewMixin, CustomNovelRUDDetailView):
    template_name = 'novelrecorder/novel_detail.html'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        charactersObject = Character.objects.filter(novel=self.get_object())
        characterSerializer = CharacterWithPrimaryDescriptionSlaveSerializer(charactersObject, many=True).data
        context.update({'characters': characterSerializer})
        return context


class NovelDetailCreateView(NovelViewMixin, CustomNovelCreateView):
    template_name = 'novelrecorder/novel_detail_create.html'
    url_to_redirect_reverse = 'novelrecorder:my_novel_list'


# The CURRENT user's novel list
@method_decorator(login_required, name='dispatch')
class UserNovelListView(NovelViewMixin, CustomNovelListCreateView):
    template_name = 'novelrecorder/my_novel_list.html'

    def get_filter_object(self):
        return self.request.user

    def get_queryset(self):
        user = self.get_filter_object()
        return Novel.objects.filter(author=user)

    def has_write_permission(self):
        return True # Need to override as the filter object is the user, not a novel object. Login required so True anyway


# Character
class CharacterViewMixin(object):
    _model_class = Character
    _writable_serializer = CharacterSerializer
    _read_only_serializer = CharacterReadOnlySerializer
    _data_name_single = 'character'
    _data_name_plural = 'characters'


class CharacterListNovelView(CharacterViewMixin, CustomNovelListCreateView):
    template_name = 'novelrecorder/character_list.html'
    _writable_serializer = CharacterWithPrimaryDescriptionSerializer
    _read_only_serializer = CharacterWithPrimaryDescriptionSerializer
    query_param_names = ['novel_id']

    def get_filter_object(self):
        return get_object_or_404(Novel, id=self.kwargs['novel_id'])

    def get_queryset(self):
        novelObj = self.get_filter_object()
        return Character.objects.filter(novel=novelObj)


# Character update doesn't redirect for now...
class CharacterCreateUpdateOnRedirectMixin(object):
    def on_redirect(self, serializer):
        if serializer and serializer.instance:
            return redirect(django.urls.reverse_lazy('novelrecorder:novel_detail', kwargs={'pk':serializer.instance.novel.id}))
        raise Http404('The character is saved but couldn''t find and redirect to the novel it belongs to.')


class CharacterDetailView(CharacterCreateUpdateOnRedirectMixin, CharacterViewMixin, CustomNovelRUDDetailView):
    template_name = 'novelrecorder/character_detail.html'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        descriptionsObject = Description.objects.filter(character=self.get_object())
        descriptionSerializer = DescriptionSlaveSerializer(descriptionsObject, many=True).data
        relationshipObject = Relationship.objects.filter(character1=self.get_object())
        relationshipSerializer = RelationshipWithPrimaryDescriptionSlaveSerializer(relationshipObject, many=True).data
        charactersWithRelationshipIDs = list(map(lambda r: r.character2.id, relationshipObject)) + [self.get_object().id]
        charactersWithoutRelationshipObject = Character.objects.filter(novel=self.get_object().getNovel()).exclude(id__in=charactersWithRelationshipIDs)
        charactersWithoutRelationshipSerializer = CharacterWithPrimaryDescriptionSlaveSerializer(charactersWithoutRelationshipObject, many=True).data
        context.update({
            'descriptions': descriptionSerializer,
            'relationships': relationshipSerializer,
            'charactersWithoutRelationship': charactersWithoutRelationshipSerializer,
        })
        return context


class CharacterDetailCreateView(CharacterCreateUpdateOnRedirectMixin, CharacterViewMixin, CustomNovelCreateView):
    template_name = 'novelrecorder/character_detail_create.html'
    _writable_serializer = CharacterCreateSerializer


class CharacterDetailDeleteView(CharacterViewMixin, CustomNovelDeleteView):
    template_name = 'novelrecorder/character_detail_delete.html'

    def on_redirect(self, serializer):
        if self.request.POST.get('novel_id'):
            return redirect(django.urls.reverse_lazy('novelrecorder:novel_detail', kwargs={'pk':self.request.POST.get('novel_id')}))
        raise Http404('The character is deleted but couldn''t find and redirect to the novel it belongs to.')


# Relationship
class RelationshipViewMixin(object):
    _model_class = Relationship
    _writable_serializer = RelationshipSerializer
    _read_only_serializer = RelationshipReadOnlySerializer
    _data_name_single = 'relationship'
    _data_name_plural = 'relationships'


class RelationshipListCharacterView(RelationshipViewMixin, CustomNovelListCreateView):
    template_name = 'novelrecorder/relationship_list.html'
    _writable_serializer = RelationshipWithPrimaryDescriptionSerializer
    _read_only_serializer = RelationshipWithPrimaryDescriptionSerializer
    query_param_names = ['character1_id', 'character2_id']

    def get_filter_object(self):
        return get_object_or_404(Character, id=self.kwargs['character1_id'])

    def get_queryset(self):
        characterObj = self.get_filter_object()
        return Relationship.objects.filter(character1=characterObj)


class RelationshipCreateUpdateOnRedirectMixin(object):
    def on_redirect(self, serializer):
        if serializer and serializer.instance:
            return redirect(django.urls.reverse_lazy('novelrecorder:character_detail', kwargs={'pk':serializer.instance.character1.id}))
        raise Http404('The description is saved but couldn''t find and redirect to the first character it belongs to.')


class RelationshipDetailView(RelationshipCreateUpdateOnRedirectMixin, RelationshipViewMixin, CustomNovelRUDDetailView):
    _writable_serializer = RelationshipPartialUpdateSerializer
    template_name = 'novelrecorder/relationship_detail.html'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        descriptionsObject = Description.objects.filter(relationship=self.get_object())
        descriptionSerializer = DescriptionSlaveSerializer(descriptionsObject, many=True).data
        context.update({'descriptions': descriptionSerializer})
        return context


class RelationshipDetailCreateView(RelationshipCreateUpdateOnRedirectMixin, RelationshipViewMixin, CustomNovelCreateView):
    template_name = 'novelrecorder/relationship_detail_create.html'
    _writable_serializer = RelationshipCreateSerializer


class RelationshipDetailDeleteView(RelationshipViewMixin, CustomNovelDeleteView):
    template_name = 'novelrecorder/relationship_detail_delete.html'

    def on_redirect(self, serializer):
        if self.request.POST.get('character1_id'):
            return redirect(django.urls.reverse_lazy('novelrecorder:character_detail', kwargs={'pk':self.request.POST.get('character1_id')}))
        raise Http404('The relationship is deleted but couldn''t find and redirect to the first character it belongs to.')


# Description
class DescriptionViewMixin(object):
    _model_class = Description
    _writable_serializer = DescriptionSerializer
    _read_only_serializer = DescriptionReadOnlySerializer
    _data_name_single = 'description'
    _data_name_plural = 'descriptions'
    

class DescriptionListCharacterView(DescriptionViewMixin, CustomNovelListCreateView):
    template_name = 'novelrecorder/description_list_character.html'
    query_param_names = ['character_id']

    def get_filter_object(self):
        return get_object_or_404(Character, id=self.kwargs['character_id'])

    def get_queryset(self):
        characterObj = self.get_filter_object()
        return Description.objects.filter(character=characterObj)

# TODO: Merge
class DescriptionListRelationshipView(DescriptionViewMixin, CustomNovelListCreateView):
    template_name = 'novelrecorder/description_list_relationship.html'
    query_param_names = ['relationship_id']

    def get_filter_object(self):
        return get_object_or_404(Relationship, id=self.kwargs['relationship_id'])

    def get_queryset(self):
        relationshipObj = self.get_filter_object()
        return Description.objects.filter(relationship=relationshipObj)


# Doesn't work for Delete - see comments on DescriptionDetailDeleteView.on_redirect().
class DescriptionCreateUpdateOnRedirectMixin(object):
    def on_redirect(self, serializer):
        if serializer and serializer.instance:
            if serializer.instance.character:
                return redirect(django.urls.reverse_lazy('novelrecorder:character_detail', kwargs={'pk':serializer.instance.character_id}))
            elif serializer.instance.relationship:
                return redirect(django.urls.reverse_lazy('novelrecorder:relationship_detail', kwargs={'pk':serializer.instance.relationship_id}))
        raise Http404('The description is saved but couldn''t find the information to redirect to the proper list page.')


class DescriptionDetailView(DescriptionCreateUpdateOnRedirectMixin, DescriptionViewMixin, CustomNovelRUDDetailView):
    _writable_serializer = DescriptionPartialUpdateSerializer
    template_name = 'novelrecorder/description_detail.html'


class DescriptionDetailCreateView(DescriptionCreateUpdateOnRedirectMixin, DescriptionViewMixin, CustomNovelCreateView):
    _writable_serializer = DescriptionCreateSerializer
    template_name = 'novelrecorder/description_detail_create.html'


class DescriptionDetailDeleteView(DescriptionViewMixin, CustomNovelDeleteView):
    template_name = 'novelrecorder/description_detail_delete.html'

    def pre_delete(self, serializer):
        # Prevent deletion if is primary description
        if self.request.POST.get('character_id'):
            masterObj = Character.objects.get(pk=self.request.POST.get('character_id'))
        elif self.request.POST.get('relationship_id'):
            masterObj = Relationship.objects.get(pk=self.request.POST.get('relationship_id'))
        else:
            raise DataErrorException('The Description to be deleted is not bound to either a character or a relationship.')
        if masterObj.getPrimaryDescription().pk == self.get_object().pk:
            raise serializers.ValidationError('You can''t delete a primary description.') # TODO 20190914: Looks like may need a better exception?

    # TODO: The same way that would work for C and U won't work for D as the instance would be non-existent at this point.
    #  For now, for D has to rely on passing context.
    #  Maybe for the sake of reducing the duplication, can see if we can convert C and U's on_redirect to do things like here (D),
    #  But not really finding this idea attractive for now.
    def on_redirect(self, serializer):
        if self.request.POST.get('character_id'):
            return redirect(django.urls.reverse_lazy('novelrecorder:character_detail', kwargs={'pk':self.request.POST.get('character_id')}))
        elif self.request.POST.get('relationship_id'):
            return redirect(django.urls.reverse_lazy('novelrecorder:relationship_detail', kwargs={'pk':self.request.POST.get('relationship_id')}))
        raise Http404('The description is deleted but couldn''t find the information to redirect to the proper list page.')
