from annoying.functions import get_object_or_None
from django.contrib.auth.models import AbstractUser
from rest_framework import permissions
from rest_framework.request import Request

from novelrecorder.constants import NUP_MINIMAL, NUP_VIEW_ONLY, NUP_DESCRIPTION_ONLY, NUP_COEDITOR
from novelrecorder.models import CustomNovelModel, NovelUserPermissionModel


class NovelUserPermission(permissions.BasePermission):
    message = 'You have no permission to view this novel.'

    # For now NovelUserPermissionModel is actually for a permissionGroup.
    # That's enough for now, only when the permission settings get more involved
    # another PermissionGroup -> Permission model would be needed.
    # Also note currently assuming permissionGroups are in order, so inequalities are used for deciding permissions.
    def custom_has_object_permission(self, user: AbstractUser, requiresWritePermission: bool, novelObj: CustomNovelModel) -> bool:
        assert isinstance(novelObj, CustomNovelModel), 'NovelUserPermission.custom_has_object_permission ' \
                                                       'called with novelObj parameter being a %s rather than ' \
                                                       'a novel object' % novelObj.__class__.__name__
        assert not isinstance(user, Request), 'NovelUserPermission.custom_has_object_permission ' \
                                              'called with user parameter being a Request -- ' \
                                              'are you trying to call has_object_permission instead?'

        novel = novelObj.getNovel()
        if user.is_anonymous:
            permissionGroup = NUP_MINIMAL  # Quite annoying, have to do this or exception.
            # Could have better way to handle? If it's only here doesn't matter, otherwise need something.
        else:
            permissionObj = get_object_or_None(NovelUserPermissionModel, novel=novel, user=user)
            if not permissionObj:
                permissionGroup = NUP_MINIMAL
            else:
                permissionGroup = permissionObj.permission

        # For superuser
        if user.is_staff:
            return True

        # All allowed if author
        if novel.author == user:
            return True

        # Allow read-only permission either the novel is public or the user has been granted enough permission
        if not requiresWritePermission and (novel.is_public or (permissionGroup >= NUP_VIEW_ONLY)):
            return True

        # For modify permissions of descriptions, allow if author or enough permission
        # TODO: This should allow only creating a new description and any modification if author
        if novelObj.isDescription() and ((novelObj.author == user) or (permissionGroup >= NUP_DESCRIPTION_ONLY)):
            return True

        # All allowed for co-editor for now
        if permissionGroup == NUP_COEDITOR:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        assert not isinstance(request, AbstractUser), 'NovelUserPermission.has_object_permission ' \
                                              'called with request parameter being a User -- ' \
                                              'are you trying to call custom_has_object_permission instead?'
        return self.custom_has_object_permission(request.user, not request.method in permissions.SAFE_METHODS, obj)