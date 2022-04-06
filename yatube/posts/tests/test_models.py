# deals/tests/tests_models.py
from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.post = Post.objects.create(
            text='Тестовый текст, нужен только для теста 12345',
            author=cls.user)

    def test_post_text(self):
        """Первые 15 символов текста поста совпадают с ожидаемыми."""
        post = PostModelTest.post
        expected = post.text[:15]
        self.assertEqual(expected, self.post.text[:15])


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовое название группы',
        )

    def test_group_title(self):
        """Название группы совпадает с ожидаемым."""
        group = GroupModelTest.group
        expected = group.title
        self.assertEqual(expected, self.group.title)
