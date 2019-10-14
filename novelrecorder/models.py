from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from novelrecorder import constants

from novelrecorder.yd_exceptions import DataErrorException


class NovelUser(AbstractUser):
    pass


class CustomModel(models.Model):
    class Meta:
        abstract = True


class CustomNovelModel(CustomModel):
    class Meta:
        abstract = True

    def getNovel(self):  # Maybe an interface instead at some stage.
        raise NotImplementedError("getNovel is not implemented for class " + self.__class__.__name__)

    def isDescription(self):
        return False

    def getPrimaryDescription(self):
        raise NotImplementedError("getPrimaryDescription is not implemented for class " + self.__class__.__name__)


class Novel(CustomNovelModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='novel_author')
    name = models.CharField(max_length=200)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ['author', 'name']

    def __str__(self):
        return self.name

    def getNovel(self):
        return self


class Character(CustomNovelModel):
    name = models.CharField(max_length=200)
    novel = models.ForeignKey(Novel, on_delete=models.PROTECT)

    class Meta:
        ordering = ['name']
        unique_together = ['novel', 'name']

    def __str__(self):
        return self.name

    def getNovel(self):
        return self.novel

    def getPrimaryDescription(self):
        return Description.objects.filter(character=self).order_by('sort_order')[0]


class Relationship(CustomNovelModel):
    character1 = models.ForeignKey(Character, on_delete=models.PROTECT, related_name='relationship_character1')
    character2 = models.ForeignKey(Character, on_delete=models.PROTECT, related_name='relationship_character2')

    class Meta:
        ordering = ['character1', 'character2']
        unique_together = ['character1', 'character2']

    def __str__(self):
        return self.character1.__str__() + " -> " + self.character2.__str__()

    def getNovel(self):
        return self.character1.getNovel()

    def getPrimaryDescription(self):
        return Description.objects.filter(relationship=self).order_by('sort_order')[0]


class Description(CustomNovelModel):
    class Meta:
        ordering = ['sort_order']

    def create(self, **obj_data):
        obj_data['sort_order'] = obj_data['id']
        return super().create(**obj_data)

    def default_is_primary(self):
        return ((self.character is not None) and Description.objects.filter(
                character=self.character).first().id == self.id) or (
                (self.relationship is not None) and Description.objects.filter(
                relationship=self.relationship).first().id == self.id)


    character = models.ForeignKey(Character, null=True, blank=True, on_delete=models.CASCADE)
    relationship = models.ForeignKey(Relationship, null=True, blank=True, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='description_author')
    title = models.CharField(max_length=200)
    content = models.TextField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)  # initialise as id on creation - see create function
    time_created = models.DateTimeField(auto_now_add=True)
    time_modified = models.DateTimeField(auto_now=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def getOwner(self):
        if (self.character is not None):
            return self.character
        elif (self.relationship is not None):
            return self.relationship
        else:
            raise DataErrorException("The description with id %s is not bound to any novel object." % (self.id))

    def getNovel(self):
        return self.getOwner().getNovel()

    def isDescription(self):
        return True


@receiver(post_save, sender=Description, dispatch_uid="initialise_description_sort_order")
# This is to initialise the sort order to the description's id.
# As currently using default id which you would only get after save.
# this is the best way I know to do this so far (assuming the sort_order is the default value, 0 by now)
def descriptionAfterSave(sender, instance, created, **kwargs):
    if created:
        if instance.sort_order == 0:
            instance.sort_order = instance.id
            instance.save()
        calculated_primary = instance.default_is_primary()
        if instance.is_primary != calculated_primary:
            instance.is_primary = calculated_primary
            instance.save()



# INTEGRITY INFO
# One and only one of the foreign keys be not null.

class NovelUserPermissionModel(CustomNovelModel):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE)
    user = models.ForeignKey(NovelUser, on_delete=models.CASCADE)
    permission = models.IntegerField(default=constants.NUP_MINIMAL)

    def getNovel(self):
        return self.novel
    # TODO: Don't think the co-editor should be able to edit this (and potentially deleting the novel), but just let them to be able to ANYTHING for now.


# class Alias

# Singletons
# TODO: maybe a separate file.
class SingletonModel(CustomModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
