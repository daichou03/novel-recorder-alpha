from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from novelrecorder.models import NovelUser, Novel, Character, Description, Relationship
from django.urls import reverse_lazy
from django.test import Client
from django.contrib.auth.hashers import make_password

# Note: Currently need to do this hack (very bad) to do any test:
#
# C:\Users\myusername\AppData\Local\Programs\Python\Python37-32\lib\unittest\loader.py:
#
# for function `_get_module_from_name(self, name):`, add:
#
#         if name.startswith('mysite.'):
#             name = name[7:]

class NovelRecorderTestCase(TestCase):

    def setUp(self):
        # TODO: When possible do them in RESTful way.
        group = Group.objects.create(name="Test Group")
        user1 = NovelUser.objects.create(username="TestUser", email="test@example.com", password=make_password("Test"))
        user2 = NovelUser.objects.create(username="AnotherUser", email="another@example.com", password=make_password("Another"))
        # API Test, not sure if works.

    # Utils and optional setups

    def loginWithResponse(self):
        c = Client()
        response = c.login(username="TestUser", email="test@example.com", password='Test')
        return (c, response)

    def login(self):
        return self.loginWithResponse()[0]

    def failOnUnexpectedIndex(self):
        self.assertEqual(True, False, 'Unexpected index when creating a testing object')

    def getDescTitle(self, index):
        return 'Test Desc Title %s' % index

    def getDescContent(self, index):
        return 'Test Desc Content %s' % index

    def createNovel(self, client, index):
        if index <= 1:
            name = 'Test Novel %s' % index
            data = {'name': name, 'is_public': True}
            client.post(reverse_lazy('novelrecorder:novel_detail_create'), data=data)
            return Novel.objects.get(name=name)
        else:
            self.failOnUnexpectedIndex()

    def createCharacter(self, client, novel, index, descIndex):
        if index <= 2:
            name = 'Test Character %s' % index
            data = {'name': name, 'novel': novel, 'des_title': self.getDescTitle(descIndex), 'des_content': self.getDescContent(descIndex)}
            client.post(reverse_lazy('novelrecorder:character_detail_create'), data=data)
            return Character.objects.get(name=name)
        else:
            self.failOnUnexpectedIndex()

    def createCharacterDescription(self, client, character, index):
        title = self.getDescTitle(index)
        data = {'character': character, 'title': title, 'content': self.getDescContent(index)}
        client.post(reverse_lazy('novelrecorder:description_detail_create'), data=data)
        return Description.objects.get(title=title)

    def createRelationshipDescription(self, client, relationship, index):
        title = self.getDescTitle(index)
        data = {'relationship': relationship, 'title': title, 'content': self.getDescContent(index)}
        client.post(reverse_lazy('novelrecorder:description_detail_create'), data=data)
        return Description.objects.get(title=title)

    def createRelationship(self, client, character1, character2, descIndex):
        data = {'character1': character1, 'character2': character2, 'des_title': self.getDescTitle(descIndex), 'des_content': self.getDescContent(descIndex)}
        client.post(reverse_lazy('novelrecorder:relationship_detail_create'), data=data)
        return Relationship.objects.get(character1=character1, character2=character2)

    # Tests
    def test_sanity(self):
        self.assertEqual(True, True)

    def test_viewIndex(self):
        response = self.client.get(reverse_lazy('novelrecorder:index'))
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        self.assertTrue(self.loginWithResponse()[1])

    def test_viewMyNovelList(self):
        c = self.login()
        response = c.get(reverse_lazy('novelrecorder:my_novel_list'))
        self.assertEqual(response.status_code, 200)

    def test_createNovel(self):
        c = self.login()
        self.createNovel(c, 1)
        self.assertEqual(Novel.objects.count(), 1)

    def test_createCharacter(self):
        c = self.login()
        novelObj = self.createNovel(c, 1)
        self.createCharacter(c, novelObj, 1, 1)
        self.assertEqual(Character.objects.count(), 1)

    def test_createCharacterDescription(self):
        c = self.login()
        novelObj = self.createNovel(c, 1)
        charaObj = self.createCharacter(c, novelObj, 1, descIndex=1)
        self.createCharacterDescription(c, charaObj, 2)
        self.assertEqual(Description.objects.count(), 2)

    def test_createRelationship(self):
        c = self.login()
        novelObj = self.createNovel(c, 1)
        charaObj1 = self.createCharacter(c, novelObj, 1, descIndex=1)
        charaObj2 = self.createCharacter(c, novelObj, 2, descIndex=2)
        self.createRelationship(c, charaObj1, charaObj2, descIndex=3)
        self.assertEqual(Relationship.objects.count(), 1)
        self.assertEqual(Description.objects.count(), 3)

    def test_createRelationshipDescription(self):
        c = self.login()
        novelObj = self.createNovel(c, 1)
        charaObj1 = self.createCharacter(c, novelObj, 1, descIndex=1)
        charaObj2 = self.createCharacter(c, novelObj, 2, descIndex=2)
        relationshipObj = self.createRelationship(c, charaObj1, charaObj2, descIndex=3)
        self.createRelationshipDescription(c, relationshipObj, 4)
        self.assertEqual(Description.objects.count(), 4)


