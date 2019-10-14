from django.urls import path, re_path
from novelrecorder import views

app_name = 'novelrecorder'

urlpatterns = [
    # ex: /novelrecorder/
    path('', views.index, name='index'),
    # Novel
    path('public_novel_list/', views.PublicNovelListView.as_view(), name='public_novel_list'),
    path('my_novel_list/', views.UserNovelListView.as_view(), name='my_novel_list'),
    path('novel_detail/<int:pk>/', views.NovelDetailView.as_view(), name='novel_detail'),
    path('novel_detail_create/', views.NovelDetailCreateView.as_view(), name='novel_detail_create'),
    # Character
    path('character_detail/<int:pk>/', views.CharacterDetailView.as_view(), name='character_detail'),
    path('character_detail_delete/<int:pk>/', views.CharacterDetailDeleteView.as_view(), name='character_detail_delete'),
    path('character_detail_create/', views.CharacterDetailCreateView.as_view(), name='character_detail_create'),
    # Relationship
    path('relationship_detail/<int:pk>/', views.RelationshipDetailView.as_view(), name='relationship_detail'),
    path('relationship_detail_delete/<int:pk>/', views.RelationshipDetailDeleteView.as_view(), name='relationship_detail_delete'),
    path('relationship_detail_create/', views.RelationshipDetailCreateView.as_view(), name='relationship_detail_create'),
    # Description
    path('description_list_character/<int:character_id>/', views.DescriptionListCharacterView.as_view(), name='description_list_character'),
    path('description_list_relationship/<int:relationship_id>/', views.DescriptionListRelationshipView.as_view(), name='description_list_relationship'),
    path('description_detail/<int:pk>/', views.DescriptionDetailView.as_view(), name='description_detail'),
    path('description_detail_delete/<int:pk>/', views.DescriptionDetailDeleteView.as_view(), name='description_detail_delete'),
    path('description_detail_create/', views.DescriptionDetailCreateView.as_view(), name='description_detail_create'),
]
